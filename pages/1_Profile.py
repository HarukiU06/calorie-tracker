import streamlit as st

from src.db.database import get_session
from src.db.models import ActivityLevel, Gender, Goal, Profile
from src.services.bmr import calc_bmr, calc_calorie_target, calc_tdee

st.title("👤 Profile")

ACTIVITY_LABELS = {
    ActivityLevel.SEDENTARY: "座りがち (×1.2)",
    ActivityLevel.LIGHTLY_ACTIVE: "軽い運動 週1-3日 (×1.375)",
    ActivityLevel.MODERATELY_ACTIVE: "中程度の運動 週3-5日 (×1.55)",
    ActivityLevel.VERY_ACTIVE: "激しい運動 週6-7日 (×1.725)",
    ActivityLevel.EXTRA_ACTIVE: "非常に激しい運動・肉体労働 (×1.9)",
}

GOAL_LABELS = {
    Goal.LOSE: "減量 (TDEE - 500 kcal)",
    Goal.MAINTAIN: "維持 (TDEE)",
    Goal.GAIN: "増量 (TDEE + 300 kcal)",
}

with get_session() as session:
    profile = session.get(Profile, 1)

with st.form("profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        gender = st.selectbox(
            "性別",
            options=[Gender.MALE, Gender.FEMALE],
            format_func=lambda x: "男性" if x == Gender.MALE else "女性",
            index=0 if (profile is None or profile.gender == Gender.MALE) else 1,
        )
        age = st.number_input("年齢", min_value=10, max_value=120, value=int(profile.age) if profile else 25)
        height_cm = st.number_input(
            "身長 (cm)", min_value=100.0, max_value=250.0,
            value=float(profile.height_cm) if profile else 170.0, step=0.1,
        )

    with col2:
        weight_kg = st.number_input(
            "体重 (kg)", min_value=20.0, max_value=300.0,
            value=float(profile.weight_kg) if profile else 65.0, step=0.1,
        )
        body_fat_pct = st.number_input(
            "体脂肪率 (%) — 空欄可",
            min_value=0.0, max_value=70.0,
            value=float(profile.body_fat_pct) if (profile and profile.body_fat_pct) else 0.0,
            step=0.1,
            help="入力すると Katch-McArdle 式で BMR を計算します。0 のままにすると無視されます。",
        )
        activity_level = st.selectbox(
            "活動レベル",
            options=list(ACTIVITY_LABELS.keys()),
            format_func=lambda x: ACTIVITY_LABELS[x],
            index=list(ACTIVITY_LABELS.keys()).index(profile.activity_level) if profile else 0,
        )
        goal = st.selectbox(
            "目標",
            options=list(GOAL_LABELS.keys()),
            format_func=lambda x: GOAL_LABELS[x],
            index=list(GOAL_LABELS.keys()).index(profile.goal) if profile else 1,
        )

    submitted = st.form_submit_button("保存", type="primary")

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
    st.success("プロフィールを保存しました。")

if profile:
    st.divider()
    st.subheader("📊 計算結果")
    bmr = calc_bmr(profile)
    tdee = calc_tdee(profile)
    target = calc_calorie_target(profile)
    method = "Katch-McArdle" if profile.body_fat_pct else "Mifflin-St Jeor"

    c1, c2, c3 = st.columns(3)
    c1.metric(f"BMR ({method})", f"{bmr:.0f} kcal")
    c2.metric("TDEE", f"{tdee:.0f} kcal")
    c3.metric("カロリー目標", f"{target:.0f} kcal")
