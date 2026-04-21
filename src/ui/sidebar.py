import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, Profile
from src.services.bmr import calc_calorie_target


def render_sidebar() -> None:
    today = datetime.date.today()

    with get_session() as session:
        profile = session.get(Profile, 1)
        entries = session.execute(
            select(MealEntry).where(MealEntry.date == today)
        ).scalars().all()

    with st.sidebar:
        st.markdown("### Today's Summary")
        if profile is None:
            st.caption("Set up your profile to see targets.")
            return

        target = calc_calorie_target(profile)
        consumed = sum(e.nutrients.get("energy_kcal", 0) for e in entries)
        remaining = target - consumed
        pct = min(consumed / target, 1.0) if target else 0

        st.progress(pct, text=f"{consumed:.0f} / {target:.0f} kcal")
        col1, col2 = st.columns(2)
        col1.metric("Consumed", f"{consumed:.0f}")
        col2.metric("Remaining", f"{remaining:.0f}")

        protein = sum(e.nutrients.get("protein_g", 0) for e in entries)
        fat = sum(e.nutrients.get("fat_g", 0) for e in entries)
        carb = sum(e.nutrients.get("carb_g", 0) for e in entries)
        st.caption(f"P {protein:.0f}g · F {fat:.0f}g · C {carb:.0f}g")
        st.divider()
