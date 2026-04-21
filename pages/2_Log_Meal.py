import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, MealType
from src.services.usda import get_food_detail, scale_nutrients, search_foods

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

# --- real-time suggest ---
def _do_search(q: str) -> None:
    if len(q) >= 2 and q != st.session_state.get("last_query"):
        try:
            st.session_state.search_results = search_foods(q)
            st.session_state.last_query = q
            st.session_state.food_detail = {}
            st.session_state.selected_food_name = ""
        except Exception as e:
            st.error(f"Search error: {e}")


query = st.text_input(
    "Food name",
    placeholder="Type at least 2 characters — e.g. egg, banana, chicken",
    key="food_query",
    on_change=lambda: _do_search(st.session_state.food_query),
)

if len(query) >= 2:
    _do_search(query)

# --- food selector ---
results: list = st.session_state.get("search_results", [])
food_detail: dict = st.session_state.get("food_detail", {})

if results:
    options = {r["description"]: r for r in results}
    prev_selection = st.session_state.get("selected_food_name", "")
    prev_index = list(options.keys()).index(prev_selection) if prev_selection in options else 0

    chosen_label = st.selectbox(
        f"Suggestions ({len(results)} found)",
        list(options.keys()),
        index=prev_index,
        key="food_select",
    )
    chosen = options[chosen_label]

    # Auto-fetch when selection changes
    if chosen_label != st.session_state.get("selected_food_name"):
        with st.spinner("Fetching nutrients..."):
            try:
                st.session_state.food_detail = get_food_detail(chosen["fdc_id"])
                st.session_state.selected_food_name = chosen_label
                food_detail = st.session_state.food_detail
            except Exception as e:
                st.error(f"Fetch error: {e}")

# --- portion input + log form ---
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

        portion_labels = [p["label"] for p in portions]
        if portion_labels:
            mode_options = ["Grams"] + portion_labels
            input_mode = st.radio("Input by", mode_options, horizontal=True)
        else:
            input_mode = "Grams"

        if input_mode == "Grams":
            grams = st.number_input("Grams", min_value=1.0, max_value=2000.0, value=100.0, step=1.0)
        else:
            selected_portion = next(p for p in portions if p["label"] == input_mode)
            count = st.number_input("Count", min_value=0.5, max_value=50.0, value=1.0, step=0.5)
            grams = count * selected_portion["grams"]
            st.caption(f"= {grams:.0f}g")

        log_submitted = st.form_submit_button("Add to log", type="primary")

    if log_submitted:
        scaled = scale_nutrients(nutrients_100g, grams)
        entry = MealEntry(
            date=log_date,
            meal_type=meal_type,
            food_name=st.session_state.selected_food_name,
            grams=round(grams, 1),
            nutrients=scaled,
        )
        with get_session() as session:
            session.add(entry)
            session.commit()
        st.success(f"Added: {st.session_state.selected_food_name} ({grams:.0f}g)")
        st.session_state.search_results = []
        st.session_state.food_detail = {}
        st.session_state.last_query = ""
        st.rerun()

# --- daily log ---
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
