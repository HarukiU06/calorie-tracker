
import streamlit as st

from src.db.database import get_session
from src.db.models import ActivityLevel, Gender, Goal, Profile
from src.services.bmr import ACTIVITY_FACTORS, calc_bmr, calc_calorie_target, calc_tdee
from src.ui.css import inject_css
from src.ui.sidebar import render_sidebar
from src.ui.theme import ACCENT, BG, BG_ALT, INK, MUTED, RULE, RULE_STRONG

st.set_page_config(page_title="Profile", layout="wide")
inject_css()
render_sidebar()

st.markdown("<h1 style='margin-bottom:1.5rem;'>Profile</h1>", unsafe_allow_html=True)

ACTIVITY_DATA = {
    ActivityLevel.SEDENTARY:         ("Sedentary",         "Little or no exercise",             "×1.2"),
    ActivityLevel.LIGHTLY_ACTIVE:    ("Lightly active",    "Light exercise 1–3 days/week",       "×1.375"),
    ActivityLevel.MODERATELY_ACTIVE: ("Moderately active", "Moderate exercise 3–5 days/week",    "×1.55"),
    ActivityLevel.VERY_ACTIVE:       ("Very active",       "Hard exercise 6–7 days/week",        "×1.725"),
    ActivityLevel.EXTRA_ACTIVE:      ("Extra active",      "Very hard exercise or physical job", "×1.9"),
}

GOAL_DATA = {
    Goal.LOSE:     ("Lose",     "−500 kcal", "~0.5 kg/week loss"),
    Goal.MAINTAIN: ("Maintain", "±0 kcal",   "Weight stable"),
    Goal.GAIN:     ("Gain",     "+300 kcal", "~0.25 kg/week gain"),
}


def _section_header(num: str, title: str) -> None:
    st.markdown(
        f"<div style='margin:1.5rem 0 0.75rem;'>"
        f"<span style='font-family:JetBrains Mono,monospace;font-size:10px;"
        f"color:{MUTED};letter-spacing:0.8px;'>{num}</span> "
        f"<span style='font-family:Inter Tight,sans-serif;font-size:18px;"
        f"font-weight:500;color:{INK};letter-spacing:-0.3px;'>{title}</span>"
        f"<div style='height:1px;background:{RULE};margin-top:6px;'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# Load existing profile
with get_session() as session:
    profile = session.get(Profile, 1)

# Initialize session state from DB or defaults
def _init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

_init("p_gender",   profile.gender if profile else Gender.MALE)
_init("p_age",      int(profile.age) if profile else 25)
_init("p_height",   float(profile.height_cm) if profile else 170.0)
_init("p_weight",   float(profile.weight_kg) if profile else 65.0)
_init("p_bf",       float(profile.body_fat_pct) if (profile and profile.body_fat_pct) else 0.0)
_init("p_activity", profile.activity_level if profile else ActivityLevel.SEDENTARY)
_init("p_goal",     profile.goal if profile else Goal.MAINTAIN)

form_col, card_col = st.columns([1, 0.6], gap="large")

with form_col:
    # ── 01 Basics ──────────────────────────────────────────────────────────────
    _section_header("01", "Basics")

    g_col, a_col = st.columns(2)
    with g_col:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;margin-bottom:2px;'>"
            f"Gender</div>",
            unsafe_allow_html=True,
        )
        gender = st.selectbox(
            "Gender", options=[Gender.MALE, Gender.FEMALE],
            format_func=lambda x: "Male" if x == Gender.MALE else "Female",
            index=0 if st.session_state.p_gender == Gender.MALE else 1,
            label_visibility="collapsed", key="p_gender",
        )

    with a_col:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;margin-bottom:2px;'>"
            f"Age <span style='color:{RULE_STRONG};'>yr</span></div>",
            unsafe_allow_html=True,
        )
        age = st.number_input(
            "Age", min_value=10, max_value=120,
            value=st.session_state.p_age, label_visibility="collapsed", key="p_age",
        )

    h_col, w_col, bf_col = st.columns(3)
    with h_col:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;margin-bottom:2px;'>"
            f"Height <span style='color:{RULE_STRONG};'>cm</span></div>",
            unsafe_allow_html=True,
        )
        height_cm = st.number_input(
            "Height", min_value=100.0, max_value=250.0,
            value=st.session_state.p_height, step=0.1,
            label_visibility="collapsed", key="p_height",
        )

    with w_col:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;margin-bottom:2px;'>"
            f"Weight <span style='color:{RULE_STRONG};'>kg</span></div>",
            unsafe_allow_html=True,
        )
        weight_kg = st.number_input(
            "Weight", min_value=20.0, max_value=300.0,
            value=st.session_state.p_weight, step=0.1,
            label_visibility="collapsed", key="p_weight",
        )

    with bf_col:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;margin-bottom:2px;'>"
            f"Body fat <span style='color:{RULE_STRONG};'>%</span></div>",
            unsafe_allow_html=True,
        )
        body_fat_pct = st.number_input(
            "Body fat", min_value=0.0, max_value=70.0,
            value=st.session_state.p_bf, step=0.1,
            label_visibility="collapsed", key="p_bf",
        )

    if body_fat_pct > 0:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;"
            f"color:{ACCENT};margin-top:4px;'>● Using Katch-McArdle</div>",
            unsafe_allow_html=True,
        )

    # ── 02 Activity level ──────────────────────────────────────────────────────
    _section_header("02", "Activity level")

    activity_html = ""
    for lvl, (name, desc, factor) in ACTIVITY_DATA.items():
        is_sel = st.session_state.p_activity == lvl
        bg = BG_ALT if is_sel else "transparent"
        dot_fill = INK if is_sel else "transparent"
        activity_html += (
            f"<div data-level='{lvl}' style='display:flex;align-items:center;"
            f"gap:12px;padding:10px 12px;border:1px solid {RULE_STRONG};"
            f"background:{bg};margin-bottom:4px;cursor:pointer;"
            f"border-radius:2px;'>"
            f"<svg width='14' height='14' viewBox='0 0 14 14'>"
            f"<circle cx='7' cy='7' r='6' fill='none' stroke='{RULE_STRONG}' stroke-width='1.5'/>"
            f"<circle cx='7' cy='7' r='3' fill='{dot_fill}'/>"
            f"</svg>"
            f"<div style='flex:1;'>"
            f"<div style='font-family:Inter Tight,sans-serif;font-size:14px;"
            f"font-weight:500;color:{INK};'>{name}</div>"
            f"<div style='font-family:Inter,sans-serif;font-size:12px;"
            f"color:{MUTED};'>{desc}</div>"
            f"</div>"
            f"<div style='font-family:JetBrains Mono,monospace;font-size:12px;"
            f"color:{MUTED};'>{factor}</div>"
            f"</div>"
        )
    st.markdown(f"<div>{activity_html}</div>", unsafe_allow_html=True)

    # Actual selectbox hidden behind the styled list (functional fallback)
    activity_level = st.selectbox(
        "Activity level",
        options=list(ACTIVITY_DATA.keys()),
        format_func=lambda x: ACTIVITY_DATA[x][0],
        index=list(ACTIVITY_DATA.keys()).index(st.session_state.p_activity),
        key="p_activity",
    )

    # ── 03 Goal ────────────────────────────────────────────────────────────────
    _section_header("03", "Goal")

    goal_cols = st.columns(3)
    for col, (g, (glabel, delta, consequence)) in zip(goal_cols, GOAL_DATA.items()):
        is_sel = st.session_state.p_goal == g
        bg = INK if is_sel else "transparent"
        color = BG if is_sel else INK
        muted_color = BG if is_sel else MUTED
        border = f"1px solid {INK if is_sel else RULE_STRONG}"
        col.markdown(
            f"<div style='padding:12px;background:{bg};border:{border};"
            f"border-radius:2px;text-align:center;'>"
            f"<div style='font-family:Inter Tight,sans-serif;font-size:16px;"
            f"font-weight:500;color:{color};'>{glabel}</div>"
            f"<div style='font-family:JetBrains Mono,monospace;font-size:12px;"
            f"color:{muted_color};margin:4px 0 2px;'>{delta}</div>"
            f"<div style='font-family:Inter,sans-serif;font-size:11px;"
            f"color:{muted_color};opacity:0.8;'>{consequence}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if col.button(glabel, key=f"goal_btn_{g}", use_container_width=True):
            st.session_state.p_goal = g
            st.rerun()

    goal = st.session_state.p_goal

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    if st.button("Save profile", type="primary"):
        with get_session() as session:
            p = session.get(Profile, 1)
            if p is None:
                p = Profile(id=1)
                session.add(p)
            p.gender = st.session_state.p_gender
            p.age = st.session_state.p_age
            p.height_cm = st.session_state.p_height
            p.weight_kg = st.session_state.p_weight
            p.body_fat_pct = st.session_state.p_bf if st.session_state.p_bf > 0 else None
            p.activity_level = st.session_state.p_activity
            p.goal = st.session_state.p_goal
            session.commit()
        st.success("Profile saved.")

# ── RIGHT: Live calc card ──────────────────────────────────────────────────────
with card_col:
    from types import SimpleNamespace
    live = SimpleNamespace(
        gender=st.session_state.p_gender,
        age=st.session_state.p_age,
        height_cm=st.session_state.p_height,
        weight_kg=st.session_state.p_weight,
        body_fat_pct=st.session_state.p_bf if st.session_state.p_bf > 0 else None,
        activity_level=st.session_state.p_activity,
        goal=st.session_state.p_goal,
    )
    bmr = calc_bmr(live)
    tdee = calc_tdee(live)
    target = calc_calorie_target(live)
    factor = ACTIVITY_FACTORS[live.activity_level]
    method = "Katch-McArdle" if live.body_fat_pct else "Mifflin-St Jeor"
    goal_adjustments = {Goal.LOSE: -500, Goal.MAINTAIN: 0, Goal.GAIN: 300}
    adjust = goal_adjustments[live.goal]
    adjust_str = f"+{adjust}" if adjust > 0 else str(adjust)

    # LBM and BMI
    lbm = live.weight_kg * (1 - (live.body_fat_pct or 0) / 100)
    bmi = live.weight_kg / ((live.height_cm / 100) ** 2)

    st.markdown(
        f"""
<div style="background:{INK};color:{BG};padding:32px;border-radius:2px;
            position:sticky;top:2rem;margin-top:3.5rem;">
  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
              letter-spacing:0.8px;opacity:0.6;margin-bottom:0.5rem;">
    YOUR DAILY TARGET
  </div>
  <div style="font-family:'Inter Tight',sans-serif;font-size:56px;
              font-weight:500;letter-spacing:-2px;line-height:1;
              margin-bottom:0.25rem;">
    {target:,.0f}
  </div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:13px;
              opacity:0.6;margin-bottom:1.25rem;">
    kcal / day
  </div>
  <div style="height:1px;background:rgba(255,255,255,0.15);margin-bottom:1rem;"></div>
  <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:1rem;">
    <div style="display:flex;justify-content:space-between;">
      <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;opacity:0.6;">BMR</div>
        <div style="font-family:'Inter',sans-serif;font-size:10px;opacity:0.4;">{method}</div>
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:14px;">{bmr:,.0f}</div>
    </div>
    <div style="display:flex;justify-content:space-between;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:11px;opacity:0.6;">
        TDEE · ×{factor}
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:14px;">{tdee:,.0f}</div>
    </div>
    <div style="display:flex;justify-content:space-between;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:11px;opacity:0.6;">
        GOAL · {adjust_str} kcal
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;">
        {target:,.0f}
      </div>
    </div>
  </div>
  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;opacity:0.4;">
    LBM = {lbm:.1f} kg · BMI = {bmi:.1f}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
