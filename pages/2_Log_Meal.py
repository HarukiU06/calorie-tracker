import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, MealType
from src.services.usda import get_food_detail, scale_nutrients, search_foods
from src.ui.sidebar import render_sidebar

st.set_page_config(page_title="Log Meal", page_icon="🍽️", layout="wide")
render_sidebar()

st.title("Log Meal")

MEAL_LABELS = {
    MealType.BREAKFAST: "Breakfast",
    MealType.LUNCH: "Lunch",
    MealType.DINNER: "Dinner",
    MealType.SNACK: "Snack",
}

NUTRIENT_DISPLAY = [
    ("energy_kcal", "Energy", "kcal"),
    ("protein_g", "Protein", "g"),
    ("fat_g", "Fat", "g"),
    ("carb_g", "Carbs", "g"),
    ("fiber_g", "Fiber", "g"),
]

log_date = st.date_input("Date", value=datetime.date.today())
st.subheader("Search and add food")

# Session state init
for key in ("search_results", "food_detail", "selected_food_name", "last_query"):
    if key not in st.session_state:
        st.session_state[key] = [] if key == "search_results" else {}  # type: ignore[assignment]
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "selected_food_name" not in st.session_state:
    st.session_state.selected_food_name = ""

query = st.text_input(
    "Food name",
    placeholder="Start typing — e.g. egg, banana, chicken breast",
    key="food_query",
)

# Auto-search when query changes (min 2 chars)
if len(query) >= 2 and query != st.session_state.get("last_query"):
    with st.spinner(""):
        try:
            st.session_state.search_results = search_foods(query)
            st.session_state.last_query = query
            st.session_state.food_detail = {}
            st.session_state.selected_food_name = ""
        except Exception as e:
            st.error(f"Search error: {e}")
elif len(query) < 2:
    st.session_state.search_results = []
    st.session_state.food_detail = {}
    st.session_state.selected_food_name = ""
    st.session_state.last_query = ""

# Inline suggestions as buttons
results: list = st.session_state.get("search_results", [])
if results and not st.session_state.food_detail:
    with st.container(border=True):
        for r in results[:10]:
            if st.button(r["description"], key=f"pick_{r['fdc_id']}", use_container_width=True):
                with st.spinner("Fetching nutrients..."):
                    try:
                        st.session_state.food_detail = get_food_detail(r["fdc_id"])
                        st.session_state.selected_food_name = r["description"]
                        st.session_state.search_results = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fetch error: {e}")

# Log form after food is selected
food_detail: dict = st.session_state.get("food_detail", {})
if food_detail:
    nutrients_100g: dict = food_detail["nutrients_per_100g"]
    portions: list = food_detail.get("portions", [])

    st.write(f"**{st.session_state.selected_food_name}** — per 100g")
    cols = st.columns(len(NUTRIENT_DISPLAY))
    for col, (key, label, unit) in zip(cols, NUTRIENT_DISPLAY):
        col.metric(label, f"{nutrients_100g.get(key, 0):.1f} {unit}")

    with st.form("log_form"):
        meal_type = st.selectbox(
            "Meal type",
            options=list(MEAL_LABELS.keys()),
            format_func=lambda x: MEAL_LABELS[x],
        )

        grams = st.number_input("Grams", min_value=1.0, max_value=2000.0, value=100.0, step=1.0)

        # Portion shortcuts — only shown when meaningful data exists
        if portions:
            st.caption("Quick fill:")
            portion_cols = st.columns(min(len(portions), 4))
            chosen_grams: float | None = None
            for i, p in enumerate(portions[:4]):
                if portion_cols[i].form_submit_button(p["label"]):
                    chosen_grams = p["grams"]

        log_submitted = st.form_submit_button("Add to log", type="primary")

    final_grams = chosen_grams if (portions and chosen_grams) else grams  # type: ignore[possibly-undefined]

    if log_submitted or (portions and chosen_grams):  # type: ignore[possibly-undefined]
        scaled = scale_nutrients(nutrients_100g, final_grams)
        entry = MealEntry(
            date=log_date,
            meal_type=meal_type,
            food_name=st.session_state.selected_food_name,
            grams=round(final_grams, 1),
            nutrients=scaled,
        )
        with get_session() as session:
            session.add(entry)
            session.commit()
        st.success(f"Added: {st.session_state.selected_food_name} ({final_grams:.0f}g)")
        st.session_state.food_detail = {}
        st.session_state.selected_food_name = ""
        st.session_state.last_query = ""
        st.rerun()

# Daily log
st.divider()
st.subheader(f"Meal log — {log_date}")

with get_session() as session:
    entries = session.execute(
        select(MealEntry).where(MealEntry.date == log_date).order_by(MealEntry.meal_type, MealEntry.id)
    ).scalars().all()

if not entries:
    st.info("No entries yet.")
else:
    for entry in entries:
        kcal = entry.nutrients.get("energy_kcal", 0)
        with st.expander(
            f"{MEAL_LABELS.get(entry.meal_type, entry.meal_type)} — "
            f"{entry.food_name} ({entry.grams}g) · {kcal:.0f} kcal"
        ):
            cols = st.columns(len(NUTRIENT_DISPLAY))
            for col, (key, label, unit) in zip(cols, NUTRIENT_DISPLAY):
                col.metric(label, f"{entry.nutrients.get(key, 0):.1f} {unit}")

            if st.button("Delete", key=f"del_{entry.id}"):
                with get_session() as session:
                    e = session.get(MealEntry, entry.id)
                    if e:
                        session.delete(e)
                        session.commit()
                st.rerun()
