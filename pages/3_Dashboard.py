import datetime

import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, Profile
from src.services.bmr import calc_calorie_target
from src.services.dri import get_dri

st.title("📊 Dashboard")

selected_date = st.date_input("日付", value=datetime.date.today())

with get_session() as session:
    profile = session.get(Profile, 1)
    entries = session.execute(
        select(MealEntry).where(MealEntry.date == selected_date)
    ).scalars().all()

if profile is None:
    st.warning("先にプロフィールを設定してください。")
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

st.subheader("🔥 カロリー")
col1, col2, col3 = st.columns(3)
col1.metric("摂取", f"{total_kcal:.0f} kcal")
col2.metric("目標", f"{calorie_target:.0f} kcal")
remaining = calorie_target - total_kcal
col3.metric("残り", f"{remaining:.0f} kcal", delta=f"{remaining:.0f}", delta_color="normal")

fig_kcal = go.Figure(go.Indicator(
    mode="gauge+number",
    value=total_kcal,
    number={"suffix": " kcal"},
    gauge={
        "axis": {"range": [0, calorie_target * 1.3]},
        "bar": {"color": "#FF6B6B"},
        "threshold": {"line": {"color": "green", "width": 3}, "thickness": 0.75, "value": calorie_target},
    },
    title={"text": "カロリー達成率"},
))
fig_kcal.update_layout(height=250, margin=dict(t=40, b=0, l=20, r=20))
st.plotly_chart(fig_kcal, use_container_width=True)

st.divider()
st.subheader("🥩 マクロ栄養素")

macros = [
    ("タンパク質", total_protein, dri.get("protein_g", 50), "protein_g", "#4ECDC4"),
    ("脂質", total_fat, dri.get("fat_g", 65), "fat_g", "#FFE66D"),
    ("炭水化物", total_carb, dri.get("carb_g", 275), "carb_g", "#A8E6CF"),
]

macro_cols = st.columns(3)
for col, (label, actual, target, _, color) in zip(macro_cols, macros):
    pct = min(actual / target * 100, 100) if target else 0
    col.metric(label, f"{actual:.1f}g", f"目標 {target:.0f}g")
    col.progress(pct / 100)

fig_macro = go.Figure(data=[
    go.Bar(
        name="摂取量",
        x=[m[0] for m in macros],
        y=[m[1] for m in macros],
        marker_color=[m[4] for m in macros],
    ),
    go.Bar(
        name="目標",
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
    st.subheader("🧬 その他の栄養素")
    DISPLAY_KEYS = [
        ("fiber_g", "食物繊維 (g)"),
        ("sodium_mg", "ナトリウム (mg)"),
        ("calcium_mg", "カルシウム (mg)"),
        ("iron_mg", "鉄 (mg)"),
        ("vitamin_c_mg", "ビタミンC (mg)"),
        ("vitamin_d_ug", "ビタミンD (μg)"),
        ("vitamin_b12_ug", "ビタミンB12 (μg)"),
    ]
    rows = []
    for key, label in DISPLAY_KEYS:
        actual = totals.get(key, 0)
        target = dri.get(key, 0)
        pct = f"{actual / target * 100:.0f}%" if target else "—"
        rows.append({"栄養素": label, "摂取量": f"{actual:.2f}", "推奨量": f"{target}", "達成率": pct})

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
