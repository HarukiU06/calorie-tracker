import streamlit as st

from src.db.database import get_session
from src.db.models import ActivityLevel, Gender, Goal, Profile
from src.services.bmr import calc_bmr, calc_calorie_target, calc_tdee
from src.ui.sidebar import render_sidebar

st.set_page_config(page_title="Profile", page_icon="👤", layout="wide")
render_sidebar()

st.title("Profile")

ACTIVITY_LABELS = {
    ActivityLevel.SEDENTARY: "Sedentary (x1.2)",
    ActivityLevel.LIGHTLY_ACTIVE: "Lightly active — 1-3 days/week (x1.375)",
    ActivityLevel.MODERATELY_ACTIVE: "Moderately active — 3-5 days/week (x1.55)",
    ActivityLevel.VERY_ACTIVE: "Very active — 6-7 days/week (x1.725)",
    ActivityLevel.EXTRA_ACTIVE: "Extra active — hard daily exercise or physical job (x1.9)",
}

GOAL_LABELS = {
    Goal.LOSE: "Lose weight (TDEE - 500 kcal)",
    Goal.MAINTAIN: "Maintain weight (TDEE)",
    Goal.GAIN: "Gain weight (TDEE + 300 kcal)",
}

with get_session() as session:
    profile = session.get(Profile, 1)

with st.form("profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        gender = st.selectbox(
            "Gender",
            options=[Gender.MALE, Gender.FEMALE],
            format_func=lambda x: "Male" if x == Gender.MALE else "Female",
            index=0 if (profile is None or profile.gender == Gender.MALE) else 1,
        )
        age = st.number_input("Age", min_value=10, max_value=120, value=int(profile.age) if profile else 25)
        height_cm = st.number_input(
            "Height (cm)", min_value=100.0, max_value=250.0,
            value=float(profile.height_cm) if profile else 170.0, step=0.1,
        )

    with col2:
        weight_kg = st.number_input(
            "Weight (kg)", min_value=20.0, max_value=300.0,
            value=float(profile.weight_kg) if profile else 65.0, step=0.1,
        )
        body_fat_pct = st.number_input(
            "Body fat % — optional",
            min_value=0.0, max_value=70.0,
            value=float(profile.body_fat_pct) if (profile and profile.body_fat_pct) else 0.0,
            step=0.1,
            help="If set, Katch-McArdle formula is used instead of Mifflin-St Jeor. Leave at 0 to ignore.",
        )
        activity_level = st.selectbox(
            "Activity level",
            options=list(ACTIVITY_LABELS.keys()),
            format_func=lambda x: ACTIVITY_LABELS[x],
            index=list(ACTIVITY_LABELS.keys()).index(profile.activity_level) if profile else 0,
        )
        goal = st.selectbox(
            "Goal",
            options=list(GOAL_LABELS.keys()),
            format_func=lambda x: GOAL_LABELS[x],
            index=list(GOAL_LABELS.keys()).index(profile.goal) if profile else 1,
        )

    submitted = st.form_submit_button("Save", type="primary")

if submitted:
    with get_session() as session:
        p = session.get(Profile, 1)
        if p is None:
            p = Profile(id=1)
            session.add(p)
        p.gender = gender
        p.age = age
        p.height_cm = height_cm
        p.weight_kg = weight_kg
        p.body_fat_pct = body_fat_pct if body_fat_pct > 0 else None
        p.activity_level = activity_level
        p.goal = goal
        session.commit()
        session.refresh(p)
        profile = p
    st.success("Profile saved.")

if profile:
    st.divider()
    st.subheader("Calculations")
    bmr = calc_bmr(profile)
    tdee = calc_tdee(profile)
    target = calc_calorie_target(profile)
    method = "Katch-McArdle" if profile.body_fat_pct else "Mifflin-St Jeor"

    c1, c2, c3 = st.columns(3)
    c1.metric(f"BMR ({method})", f"{bmr:.0f} kcal")
    c2.metric("TDEE", f"{tdee:.0f} kcal")
    c3.metric("Calorie target", f"{target:.0f} kcal")
