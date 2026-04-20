import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, MealType
from src.services.usda import get_nutrients_per_100g, scale_nutrients, search_foods

st.title("🍽️ 食事ログ")

MEAL_LABELS = {
    MealType.BREAKFAST: "朝食",
    MealType.LUNCH: "昼食",
    MealType.DINNER: "夕食",
    MealType.SNACK: "間食",
}

log_date = st.date_input("日付", value=datetime.date.today())

st.subheader("食材を検索して追加")

query = st.text_input("食材名を入力 (英語推奨)", placeholder="e.g. chicken breast")

if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "selected_nutrients" not in st.session_state:
    st.session_state.selected_nutrients = {}
if "selected_food_name" not in st.session_state:
    st.session_state.selected_food_name = ""

if st.button("検索") and query:
    with st.spinner("検索中..."):
        try:
            results = search_foods(query)
            st.session_state.search_results = results
            st.session_state.selected_nutrients = {}
        except Exception as e:
            st.error(f"検索エラー: {e}")

if st.session_state.search_results:
    options = {f"{r['description']} (id:{r['fdc_id']})": r for r in st.session_state.search_results}
    chosen_label = st.selectbox("検索結果", list(options.keys()))
    chosen = options[chosen_label]

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("栄養素を取得"):
            with st.spinner("取得中..."):
                try:
                    st.session_state.selected_nutrients = get_nutrients_per_100g(chosen["fdc_id"])
                    st.session_state.selected_food_name = chosen["description"]
                except Exception as e:
                    st.error(f"取得エラー: {e}")

    if st.session_state.selected_nutrients:
        st.write(f"**{st.session_state.selected_food_name}** (per 100g)")
        nutrient_preview = {
            k: v for k, v in st.session_state.selected_nutrients.items()
            if k in ("energy_kcal", "protein_g", "fat_g", "carb_g")
        }
        st.json(nutrient_preview)

        with st.form("log_form"):
            meal_type = st.selectbox(
                "食事区分",
                options=list(MEAL_LABELS.keys()),
                format_func=lambda x: MEAL_LABELS[x],
            )
            grams = st.number_input("グラム数", min_value=1.0, max_value=2000.0, value=100.0, step=1.0)
            log_submitted = st.form_submit_button("ログに追加", type="primary")

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
            st.success(f"「{st.session_state.selected_food_name}」を追加しました。")
            st.session_state.search_results = []
            st.session_state.selected_nutrients = {}
            st.rerun()

st.divider()
st.subheader(f"📋 {log_date} の食事記録")

with get_session() as session:
    entries = session.execute(
        select(MealEntry).where(MealEntry.date == log_date).order_by(MealEntry.meal_type, MealEntry.id)
    ).scalars().all()

if not entries:
    st.info("まだ記録がありません。")
else:
    for entry in entries:
        with st.expander(f"{MEAL_LABELS.get(entry.meal_type, entry.meal_type)} — {entry.food_name} ({entry.grams}g)"):
            kcal = entry.nutrients.get("energy_kcal", 0)
            protein = entry.nutrients.get("protein_g", 0)
            fat = entry.nutrients.get("fat_g", 0)
            carb = entry.nutrients.get("carb_g", 0)
            st.write(f"エネルギー: **{kcal:.1f} kcal** | タンパク質: {protein:.1f}g | 脂質: {fat:.1f}g | 炭水化物: {carb:.1f}g")

            if st.button("削除", key=f"del_{entry.id}"):
                with get_session() as session:
                    e = session.get(MealEntry, entry.id)
                    if e:
                        session.delete(e)
                        session.commit()
                st.rerun()
