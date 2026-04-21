import datetime

import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, Profile
from src.ui.sidebar import render_sidebar

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
render_sidebar()
from src.services.bmr import calc_calorie_target
from src.services.dri import get_dri

st.title("Dashboard")

selected_date = st.date_input("Date", value=datetime.date.today())

with get_session() as session:
    profile = session.get(Profile, 1)
    entries = session.execute(
        select(MealEntry).where(MealEntry.date == selected_date)
    ).scalars().all()

if profile is None:
    st.warning("Please set up your profile first.")
    st.stop()

calorie_target = calc_calorie_target(profile)
dri = get_dri(profile)

totals: dict[str, float] = {}
for entry in entries:
    for k, v in entry.nutrients.items():
        totals[k] = totals.get(k, 0) + v

total_kcal = totals.get("energy_kcal", 0)
total_protein = totals.get("protein_g", 0)
total_fat = totals.get("fat_g", 0)
total_carb = totals.get("carb_g", 0)

st.subheader("Calories")
col1, col2, col3 = st.columns(3)
col1.metric("Consumed", f"{total_kcal:.0f} kcal")
col2.metric("Target", f"{calorie_target:.0f} kcal")
remaining = calorie_target - total_kcal
col3.metric("Remaining", f"{remaining:.0f} kcal", delta=f"{remaining:.0f}", delta_color="normal")

fig_kcal = go.Figure(go.Indicator(
    mode="gauge+number",
    value=total_kcal,
    number={"suffix": " kcal"},
    gauge={
        "axis": {"range": [0, calorie_target * 1.3]},
        "bar": {"color": "#FF6B6B"},
        "threshold": {"line": {"color": "green", "width": 3}, "thickness": 0.75, "value": calorie_target},
    },
    title={"text": "Calorie progress"},
))
fig_kcal.update_layout(height=250, margin=dict(t=40, b=0, l=20, r=20))
st.plotly_chart(fig_kcal, use_container_width=True)

st.divider()
st.subheader("Macronutrients")

macros = [
    ("Protein", total_protein, dri.get("protein_g", 50), "#4ECDC4"),
    ("Fat", total_fat, dri.get("fat_g", 65), "#FFE66D"),
    ("Carbs", total_carb, dri.get("carb_g", 275), "#A8E6CF"),
]

macro_cols = st.columns(3)
for col, (label, actual, target, color) in zip(macro_cols, macros):
    pct = min(actual / target * 100, 100) if target else 0
    col.metric(label, f"{actual:.1f}g", f"target {target:.0f}g")
    col.progress(pct / 100)

fig_macro = go.Figure(data=[
    go.Bar(
        name="Consumed",
        x=[m[0] for m in macros],
        y=[m[1] for m in macros],
        marker_color=[m[3] for m in macros],
    ),
    go.Bar(
        name="Target",
        x=[m[0] for m in macros],
        y=[m[2] for m in macros],
        marker_color="rgba(200,200,200,0.4)",
    ),
])
fig_macro.update_layout(
    barmode="overlay",
    height=300,
    margin=dict(t=20, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig_macro, use_container_width=True)

if totals:
    st.divider()
    st.subheader("Other nutrients")
    DISPLAY_KEYS = [
        ("fiber_g", "Fiber (g)"),
        ("sodium_mg", "Sodium (mg)"),
        ("calcium_mg", "Calcium (mg)"),
        ("iron_mg", "Iron (mg)"),
        ("vitamin_c_mg", "Vitamin C (mg)"),
        ("vitamin_d_ug", "Vitamin D (μg)"),
        ("vitamin_b12_ug", "Vitamin B12 (μg)"),
    ]
    rows = []
    for key, label in DISPLAY_KEYS:
        actual = totals.get(key, 0)
        target = dri.get(key, 0)
        pct = f"{actual / target * 100:.0f}%" if target else "—"
        rows.append({"Nutrient": label, "Consumed": f"{actual:.2f}", "Recommended": f"{target}", "Progress": pct})

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
