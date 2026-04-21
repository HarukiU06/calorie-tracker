import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, Profile
from src.services.bmr import calc_calorie_target
from src.ui.theme import ACCENT, INK, MUTED, RULE_STRONG


def render_sidebar() -> None:
    today = datetime.date.today()

    with get_session() as session:
        profile = session.get(Profile, 1)
        entries = session.execute(
            select(MealEntry).where(MealEntry.date == today)
        ).scalars().all()

    consumed = sum(e.nutrients.get("energy_kcal", 0) for e in entries)
    target = calc_calorie_target(profile) if profile else 2000.0
    remaining = target - consumed
    pct = min(consumed / target, 1.0) if target else 0
    protein = sum(e.nutrients.get("protein_g", 0) for e in entries)
    fat = sum(e.nutrients.get("fat_g", 0) for e in entries)
    carb = sum(e.nutrients.get("carb_g", 0) for e in entries)

    date_str = today.strftime("%d %b %Y").upper()

    with st.sidebar:
        st.markdown(
            f"""
<div style="margin-bottom:1.5rem;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.25rem;">
    <div style="width:10px;height:10px;background:{ACCENT};flex-shrink:0;"></div>
    <span style="font-family:'Inter Tight',sans-serif;font-weight:600;font-size:14px;
                 color:{INK};letter-spacing:-0.3px;">Calorie Tracker</span>
  </div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:{MUTED};
              letter-spacing:0.6px;margin-left:18px;">TODAY · {date_str}</div>
</div>

<div style="margin-bottom:0.5rem;">
  <span style="font-family:'Inter Tight',sans-serif;font-size:30px;font-weight:500;
               color:{INK};letter-spacing:-1px;">{consumed:,.0f}</span>
  <span style="font-family:'JetBrains Mono',monospace;font-size:13px;color:{MUTED};
               margin-left:4px;">/ {target:,.0f} kcal</span>
</div>

<div style="position:relative;height:3px;background:{RULE_STRONG};
            margin-bottom:0.4rem;border-radius:0;">
  <div style="position:absolute;left:0;top:0;height:3px;
              width:{pct*100:.1f}%;background:{ACCENT};border-radius:0;
              transition:width 0.3s ease;"></div>
</div>

<div style="font-family:'JetBrains Mono',monospace;font-size:11px;
            color:{MUTED};margin-bottom:1.25rem;">
  {remaining:,.0f} kcal remaining
</div>

<div style="font-family:'JetBrains Mono',monospace;font-size:12px;
            display:flex;gap:12px;padding-bottom:1.25rem;
            border-bottom:1px solid {RULE_STRONG};">
  <span><span style="color:{INK};font-weight:500;">P</span>
        <span style="color:{MUTED};">&thinsp;{protein:.0f}g</span></span>
  <span><span style="color:{INK};font-weight:500;">F</span>
        <span style="color:{MUTED};">&thinsp;{fat:.0f}g</span></span>
  <span><span style="color:{INK};font-weight:500;">C</span>
        <span style="color:{MUTED};">&thinsp;{carb:.0f}g</span></span>
</div>
""",
            unsafe_allow_html=True,
        )
