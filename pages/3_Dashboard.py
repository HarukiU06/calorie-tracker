import datetime
import math

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, MealType, Profile
from src.services.bmr import calc_calorie_target
from src.services.dri import get_dri
from src.ui.css import inject_css
from src.ui.sidebar import render_sidebar
from src.ui.theme import ACCENT, BG, INK, MUTED, RULE, RULE_STRONG

st.set_page_config(page_title="Dashboard", layout="wide")
inject_css()
render_sidebar()

# ── Date toolbar ──────────────────────────────────────────────────────────────
if "dash_date" not in st.session_state:
    st.session_state.dash_date = datetime.date.today()

tb_r, tb_c, tb_l = st.columns([4, 2, 1])
with tb_c:
    selected_date: datetime.date = st.date_input(
        "", value=st.session_state.dash_date, label_visibility="collapsed", key="dash_date_input"
    )
    st.session_state.dash_date = selected_date
with tb_l:
    if st.button("Today", key="dash_today"):
        st.session_state.dash_date = datetime.date.today()
        st.rerun()

st.markdown("<h1 style='margin-top:0.5rem;'>Dashboard</h1>", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
with get_session() as session:
    profile = session.get(Profile, 1)
    entries = session.execute(
        select(MealEntry).where(MealEntry.date == st.session_state.dash_date)
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
remaining = calorie_target - total_kcal
pct = min(total_kcal / calorie_target, 1.0) if calorie_target else 0

# ── Calorie ring ──────────────────────────────────────────────────────────────
R = 92
STROKE = 10
circumference = 2 * math.pi * R
arc_len = circumference * pct
gap = circumference - arc_len

ring_col, macro_col = st.columns([1, 2])

with ring_col:
    st.markdown(
        f"""
<div style="display:flex;justify-content:center;padding:1rem 0;">
<svg width="260" height="260" viewBox="0 0 260 260">
  <!-- background ring -->
  <circle cx="130" cy="130" r="{R}"
    fill="none" stroke="{RULE_STRONG}" stroke-width="3"/>
  <!-- foreground arc -->
  <circle cx="130" cy="130" r="{R}"
    fill="none" stroke="{ACCENT}" stroke-width="{STROKE}"
    stroke-linecap="round"
    stroke-dasharray="{arc_len:.2f} {gap:.2f}"
    transform="rotate(-90 130 130)"/>
  <!-- center labels -->
  <text x="130" y="112" text-anchor="middle"
    font-family="JetBrains Mono,monospace" font-size="11"
    fill="{MUTED}" letter-spacing="0.8">REMAINING</text>
  <text x="130" y="152" text-anchor="middle"
    font-family="Inter Tight,sans-serif" font-size="52" font-weight="500"
    fill="{INK}">{remaining:,.0f}</text>
  <text x="130" y="175" text-anchor="middle"
    font-family="JetBrains Mono,monospace" font-size="13"
    fill="{MUTED}">of {calorie_target:,.0f} kcal</text>
</svg>
</div>
""",
        unsafe_allow_html=True,
    )

# ── Macro 4-up ────────────────────────────────────────────────────────────────
with macro_col:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    MACROS = [
        ("PROTEIN", totals.get("protein_g", 0), dri.get("protein_g", 50), "g"),
        ("FAT",     totals.get("fat_g", 0),     dri.get("fat_g", 65),    "g"),
        ("CARBS",   totals.get("carb_g", 0),    dri.get("carb_g", 275),  "g"),
        ("FIBER",   totals.get("fiber_g", 0),   dri.get("fiber_g", 28),  "g"),
    ]
    cols = st.columns(4)
    for col, (label, actual, target, unit) in zip(cols, MACROS):
        bar_pct = min(actual / target, 1.0) if target else 0
        pct_label = f"{bar_pct*100:.0f}%"
        low = actual < target
        bar_color = ACCENT if low else INK
        col.markdown(
            f"""
<div style="padding:0.5rem 0;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;
              margin-bottom:4px;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                 color:{MUTED};letter-spacing:0.8px;">{label}</span>
    <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                 color:{MUTED};">{pct_label}</span>
  </div>
  <div style="font-family:'Inter Tight',sans-serif;font-size:24px;
              font-weight:500;color:{INK};letter-spacing:-0.5px;line-height:1.1;">
    {actual:.1f}
    <span style="font-family:'JetBrains Mono',monospace;font-size:12px;
                 color:{MUTED};font-weight:400;">/ {target:.0f}{unit}</span>
  </div>
  <div style="position:relative;height:3px;background:{RULE_STRONG};
              margin-top:8px;border-radius:0;">
    <div style="position:absolute;left:0;top:0;height:3px;width:{bar_pct*100:.1f}%;
                background:{bar_color};border-radius:0;"></div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown(f"<hr style='border-top:1px solid {RULE};margin:1.5rem 0;'>", unsafe_allow_html=True)

# ── Meals list ────────────────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='font-size:15px;letter-spacing:0.6px;font-family:JetBrains Mono,monospace;"
    f"color:{MUTED};text-transform:uppercase;font-weight:400;margin-bottom:1rem;'>Meals</h2>",
    unsafe_allow_html=True,
)

MEAL_ORDER = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACK]
MEAL_LABELS = {
    MealType.BREAKFAST: "Breakfast",
    MealType.LUNCH:     "Lunch",
    MealType.DINNER:    "Dinner",
    MealType.SNACK:     "Snack",
}

by_meal: dict[str, list] = {m: [] for m in MEAL_ORDER}
for e in entries:
    if e.meal_type in by_meal:
        by_meal[e.meal_type].append(e)

rows_html = ""
for meal_type in MEAL_ORDER:
    meal_entries = by_meal[meal_type]
    label = MEAL_LABELS[meal_type]
    subtotal = sum(e.nutrients.get("energy_kcal", 0) for e in meal_entries)

    if meal_entries:
        items_html = "".join(
            f"<div style='padding:2px 0;font-family:Inter,sans-serif;font-size:14px;color:{INK};'>"
            f"{e.food_name} "
            f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:{MUTED};'>"
            f"({e.grams:.0f}g)</span></div>"
            for e in meal_entries
        )
        kcal_html = (
            f"<span style='font-family:JetBrains Mono,monospace;font-size:13px;"
            f"color:{INK};font-weight:500;'>{subtotal:.0f}</span>"
            f"<span style='font-family:JetBrains Mono,monospace;font-size:11px;"
            f"color:{MUTED};'> kcal</span>"
        )
    else:
        items_html = (
            f"<span style='font-style:italic;font-family:Inter,sans-serif;"
            f"font-size:13px;color:{MUTED};'>Not logged yet</span>"
        )
        kcal_html = f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:{MUTED};'>—</span>"

    rows_html += f"""
<div style="display:grid;grid-template-columns:100px 1fr auto;gap:1rem;
            padding:0.75rem 0;border-top:1px solid {RULE};align-items:start;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:11px;
              color:{MUTED};letter-spacing:0.4px;padding-top:3px;">{label.upper()}</div>
  <div>{items_html}</div>
  <div style="text-align:right;padding-top:3px;">{kcal_html}</div>
</div>
"""

st.markdown(f"<div>{rows_html}</div>", unsafe_allow_html=True)

st.markdown(f"<hr style='border-top:1px solid {RULE};margin:1.5rem 0;'>", unsafe_allow_html=True)

# ── Micronutrients ─────────────────────────────────────────────────────────────
st.markdown(
    f"<h2 style='font-size:15px;letter-spacing:0.6px;font-family:JetBrains Mono,monospace;"
    f"color:{MUTED};text-transform:uppercase;font-weight:400;margin-bottom:1rem;'>Micronutrients</h2>",
    unsafe_allow_html=True,
)

MICRO_KEYS = [
    ("sodium_mg",    "Sodium",    "mg"),
    ("calcium_mg",   "Calcium",   "mg"),
    ("iron_mg",      "Iron",      "mg"),
    ("vitamin_c_mg", "Vitamin C", "mg"),
    ("vitamin_d_ug", "Vitamin D", "μg"),
    ("vitamin_b12_ug","Vitamin B12","μg"),
    ("folate_ug",    "Folate",    "μg"),
    ("potassium_mg", "Potassium", "mg"),
]

low_nutrients = []
micro_rows = ""
for key, label, unit in MICRO_KEYS:
    actual = totals.get(key, 0)
    target = dri.get(key, 0)
    if not target:
        continue
    raw_pct = actual / target
    bar_pct = min(raw_pct, 1.2)  # cap axis at 120%
    display_pct = raw_pct * 100
    bar_color = ACCENT if raw_pct < 1.0 else INK
    tick_pos = min(100 / 120, 1.0) * 100  # 100% mark on 120% axis

    if raw_pct < 0.5:
        low_nutrients.append((label, display_pct, unit, key))

    micro_rows += f"""
<div style="display:grid;grid-template-columns:130px 1fr 110px;gap:1rem;
            padding:0.5rem 0;border-bottom:1px solid {RULE};align-items:center;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:{INK};">{label}</div>
  <div style="position:relative;height:3px;background:{RULE_STRONG};border-radius:0;">
    <div style="position:absolute;left:0;top:0;height:3px;
                width:{bar_pct/1.2*100:.1f}%;background:{bar_color};border-radius:0;"></div>
    <div style="position:absolute;left:{tick_pos:.1f}%;top:-3px;
                width:1px;height:9px;background:{MUTED};opacity:0.5;"></div>
  </div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:12px;
              color:{MUTED};text-align:right;">
    {actual:.1f}<span style="opacity:0.5;">/{target:.0f}{unit}</span>
  </div>
</div>
"""

st.markdown(f"<div>{micro_rows}</div>", unsafe_allow_html=True)

if low_nutrients:
    label, pct_val, unit, _ = low_nutrients[0]
    suggestions = {
        "Iron": "red meat, legumes, or fortified cereals",
        "Calcium": "dairy, leafy greens, or fortified plant milk",
        "Vitamin D": "fatty fish, eggs, or sunlight exposure",
        "Vitamin C": "citrus fruit, bell peppers, or broccoli",
        "Vitamin B12": "meat, fish, dairy, or fortified foods",
        "Folate": "leafy greens, beans, or fortified grains",
        "Potassium": "bananas, potatoes, or legumes",
        "Sodium": "processed foods or table salt",
    }
    suggestion = suggestions.get(label, "a varied diet")
    st.markdown(
        f"""
<div style="margin-top:1rem;padding:0.75rem 1rem;background:{BG};
            border-left:2px solid {ACCENT};font-family:'JetBrains Mono',monospace;
            font-size:12px;color:{MUTED};">
  Low: <strong style="color:{INK};">{label}</strong> is at {pct_val:.0f}% of target
  — consider {suggestion}.
</div>
""",
        unsafe_allow_html=True,
    )
