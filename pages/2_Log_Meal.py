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

query = st.text_input("Food name", placeholder="e.g. egg, chicken breast, banana")

if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "food_detail" not in st.session_state:
    st.session_state.food_detail = {}
if "selected_food_name" not in st.session_state:
    st.session_state.selected_food_name = ""

if st.button("Search") and query:
    with st.spinner("Searching..."):
        try:
            st.session_state.search_results = search_foods(query)
            st.session_state.food_detail = {}
        except Exception as e:
            st.error(f"Search error: {e}")

if st.session_state.search_results:
    options = {r["description"]: r for r in st.session_state.search_results}
    chosen_label = st.selectbox("Results", list(options.keys()))
    chosen = options[chosen_label]

    if st.button("Fetch nutrients"):
        with st.spinner("Fetching..."):
            try:
                st.session_state.food_detail = get_food_detail(chosen["fdc_id"])
                st.session_state.selected_food_name = chosen["description"]
            except Exception as e:
                st.error(f"Fetch error: {e}")

    detail = st.session_state.food_detail
    if detail:
        nutrients_100g = detail["nutrients_per_100g"]
        serving_g: float | None = detail.get("serving_g")
        serving_label: str = detail.get("serving_label", "")

        st.write(f"**{st.session_state.selected_food_name}** — per 100g")
        cols = st.columns(len(NUTRIENT_DISPLAY))
        for col, (key, label, unit) in zip(cols, NUTRIENT_DISPLAY):
            val = nutrients_100g.get(key, 0)
            col.metric(label, f"{val:.1f} {unit}")

        with st.form("log_form"):
            meal_type = st.selectbox(
                "Meal type",
                options=list(MEAL_LABELS.keys()),
                format_func=lambda x: MEAL_LABELS[x],
            )

            input_mode_options = ["Grams"]
            if serving_g:
                input_mode_options.append(f"Servings ({serving_label})")
            input_mode = st.radio("Input by", input_mode_options, horizontal=True)

            if input_mode == "Grams":
                grams = st.number_input("Grams", min_value=1.0, max_value=2000.0, value=100.0, step=1.0)
            else:
                pieces = st.number_input("Number of servings", min_value=0.5, max_value=50.0, value=1.0, step=0.5)
                grams = pieces * serving_g  # type: ignore[operator]
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
            st.rerun()

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
                val = entry.nutrients.get(key, 0)
                col.metric(label, f"{val:.1f} {unit}")

            if st.button("Delete", key=f"del_{entry.id}"):
                with get_session() as session:
                    e = session.get(MealEntry, entry.id)
                    if e:
                        session.delete(e)
                        session.commit()
                st.rerun()
