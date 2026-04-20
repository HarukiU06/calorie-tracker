import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, MealType
from src.services.usda import get_nutrients_per_100g, scale_nutrients, search_foods

st.title("Log Meal")

MEAL_LABELS = {
    MealType.BREAKFAST: "Breakfast",
    MealType.LUNCH: "Lunch",
    MealType.DINNER: "Dinner",
    MealType.SNACK: "Snack",
}

log_date = st.date_input("Date", value=datetime.date.today())

st.subheader("Search and add food")

query = st.text_input("Food name", placeholder="e.g. chicken breast")

if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_nutrients" not in st.session_state:
    st.session_state.selected_nutrients = {}
if "selected_food_name" not in st.session_state:
    st.session_state.selected_food_name = ""

if st.button("Search") and query:
    with st.spinner("Searching..."):
        try:
            results = search_foods(query)
            st.session_state.search_results = results
            st.session_state.selected_nutrients = {}
        except Exception as e:
            st.error(f"Search error: {e}")

if st.session_state.search_results:
    options = {f"{r['description']} (id:{r['fdc_id']})": r for r in st.session_state.search_results}
    chosen_label = st.selectbox("Results", list(options.keys()))
    chosen = options[chosen_label]

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Fetch nutrients"):
            with st.spinner("Fetching..."):
                try:
                    st.session_state.selected_nutrients = get_nutrients_per_100g(chosen["fdc_id"])
                    st.session_state.selected_food_name = chosen["description"]
                except Exception as e:
                    st.error(f"Fetch error: {e}")

    if st.session_state.selected_nutrients:
        st.write(f"**{st.session_state.selected_food_name}** (per 100g)")
        nutrient_preview = {
            k: v for k, v in st.session_state.selected_nutrients.items()
            if k in ("energy_kcal", "protein_g", "fat_g", "carb_g")
        }
        st.json(nutrient_preview)

        with st.form("log_form"):
            meal_type = st.selectbox(
                "Meal type",
                options=list(MEAL_LABELS.keys()),
                format_func=lambda x: MEAL_LABELS[x],
            )
            grams = st.number_input("Grams", min_value=1.0, max_value=2000.0, value=100.0, step=1.0)
            log_submitted = st.form_submit_button("Add to log", type="primary")

        if log_submitted:
            scaled = scale_nutrients(st.session_state.selected_nutrients, grams)
            entry = MealEntry(
                date=log_date,
                meal_type=meal_type,
                food_name=st.session_state.selected_food_name,
                grams=grams,
                nutrients=scaled,
            )
            with get_session() as session:
                session.add(entry)
                session.commit()
            st.success(f"Added: {st.session_state.selected_food_name}")
            st.session_state.search_results = []
            st.session_state.selected_nutrients = {}
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
        with st.expander(f"{MEAL_LABELS.get(entry.meal_type, entry.meal_type)} — {entry.food_name} ({entry.grams}g)"):
            kcal = entry.nutrients.get("energy_kcal", 0)
            protein = entry.nutrients.get("protein_g", 0)
            fat = entry.nutrients.get("fat_g", 0)
            carb = entry.nutrients.get("carb_g", 0)
            st.write(f"Energy: **{kcal:.1f} kcal** | Protein: {protein:.1f}g | Fat: {fat:.1f}g | Carbs: {carb:.1f}g")

            if st.button("Delete", key=f"del_{entry.id}"):
                with get_session() as session:
                    e = session.get(MealEntry, entry.id)
                    if e:
                        session.delete(e)
                        session.commit()
                st.rerun()
