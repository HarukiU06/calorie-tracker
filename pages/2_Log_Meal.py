import datetime

import streamlit as st
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import MealEntry, MealType
from src.services.usda import get_food_detail, scale_nutrients, search_foods
from src.ui.css import inject_css
from src.ui.sidebar import render_sidebar
from src.ui.theme import INK, MUTED, RULE, RULE_STRONG

st.set_page_config(page_title="Log Meal", layout="wide")
inject_css()
render_sidebar()

st.markdown("<h1 style='margin-bottom:1.5rem;'>Log Meal</h1>", unsafe_allow_html=True)

MEAL_TYPES = [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACK]
MEAL_LABELS = {
    MealType.BREAKFAST: "Breakfast",
    MealType.LUNCH:     "Lunch",
    MealType.DINNER:    "Dinner",
    MealType.SNACK:     "Snack",
}

# Session state init
for key, default in [
    ("search_results", []),
    ("food_detail", {}),
    ("selected_food_name", ""),
    ("selected_fdc_id", None),
    ("last_query", ""),
    ("log_grams", 100.0),
    ("log_meal_type", MealType.BREAKFAST),
]:
    if key not in st.session_state:
        st.session_state[key] = default

log_date = st.date_input("Date", value=datetime.date.today(), label_visibility="collapsed", key="log_date")

left_col, right_col = st.columns([1, 1], gap="large")

# ── LEFT: Search ───────────────────────────────────────────────────────────────
with left_col:
    st.markdown(
        f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
        f"letter-spacing:0.8px;color:{MUTED};text-transform:uppercase;"
        f"margin-bottom:4px;'>Food name</div>",
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Food name", placeholder="e.g. egg, banana, chicken breast",
        label_visibility="collapsed", key="food_query",
    )

    # Auto-search
    if len(query) >= 2 and query != st.session_state.last_query:
        try:
            st.session_state.search_results = search_foods(query)
            st.session_state.last_query = query
            st.session_state.food_detail = {}
            st.session_state.selected_food_name = ""
        except Exception as e:
            st.error(f"Search error: {e}")
    elif len(query) < 2:
        st.session_state.search_results = []
        st.session_state.food_detail = {}
        st.session_state.selected_food_name = ""
        st.session_state.last_query = ""

    results: list = st.session_state.search_results
    if results:
        n = len(results)
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.6px;margin:8px 0 4px;'>"
            f"{n} RESULTS · USDA FOODDATA CENTRAL</div>",
            unsafe_allow_html=True,
        )

        if not st.session_state.food_detail:
            for r in results[:10]:
                is_selected = r["description"] == st.session_state.selected_food_name
                bg = INK if is_selected else "transparent"
                color = "#f7f5f0" if is_selected else INK
                border = f"1px solid {RULE_STRONG}"

                if st.button(
                    r["description"],
                    key=f"pick_{r['fdc_id']}",
                    use_container_width=True,
                ):
                    with st.spinner(""):
                        try:
                            st.session_state.food_detail = get_food_detail(r["fdc_id"])
                            st.session_state.selected_food_name = r["description"]
                            st.session_state.selected_fdc_id = r["fdc_id"]
                            st.session_state.log_grams = 100.0
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fetch error: {e}")

    # Today's log (compact)
    st.markdown(f"<hr style='border-top:1px solid {RULE};margin:1.5rem 0 1rem;'>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
        f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;"
        f"margin-bottom:8px;'>Today's log</div>",
        unsafe_allow_html=True,
    )

    with get_session() as session:
        today_entries = session.execute(
            select(MealEntry)
            .where(MealEntry.date == log_date)
            .order_by(MealEntry.meal_type, MealEntry.id)
        ).scalars().all()

    if not today_entries:
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:12px;"
            f"color:{MUTED};font-style:italic;'>No entries yet.</div>",
            unsafe_allow_html=True,
        )
    else:
        log_html = ""
        for e in today_entries:
            initial = e.meal_type[0].upper()
            kcal = e.nutrients.get("energy_kcal", 0)
            log_html += (
                f"<div style='display:flex;justify-content:space-between;"
                f"font-family:JetBrains Mono,monospace;font-size:12px;"
                f"color:{MUTED};padding:3px 0;border-bottom:1px solid {RULE};'>"
                f"<span><b style='color:{INK};'>{initial}</b> {e.food_name}</span>"
                f"<span>{kcal:.0f} kcal</span></div>"
            )
        st.markdown(f"<div>{log_html}</div>", unsafe_allow_html=True)

# ── RIGHT: Composer ────────────────────────────────────────────────────────────
with right_col:
    food_detail: dict = st.session_state.food_detail
    if not food_detail:
        st.markdown(
            f"<div style='padding:2rem;border:1px solid {RULE_STRONG};"
            f"font-family:JetBrains Mono,monospace;font-size:12px;"
            f"color:{MUTED};text-align:center;letter-spacing:0.4px;'>"
            f"Search and select a food to log</div>",
            unsafe_allow_html=True,
        )
    else:
        nutrients_100g = food_detail["nutrients_per_100g"]
        portions: list = food_detail.get("portions", [])
        fdc_id = st.session_state.selected_fdc_id

        # Header
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;"
            f"margin-bottom:4px;'>Selected</div>"
            f"<div style='font-family:Inter Tight,sans-serif;font-size:20px;"
            f"font-weight:500;color:{INK};letter-spacing:-0.4px;margin-bottom:4px;'>"
            f"{st.session_state.selected_food_name}</div>"
            f"<div style='font-family:JetBrains Mono,monospace;font-size:11px;"
            f"color:{MUTED};margin-bottom:1.25rem;'>FDC #{fdc_id}</div>",
            unsafe_allow_html=True,
        )

        # Amount
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;"
            f"margin-bottom:4px;'>Amount</div>",
            unsafe_allow_html=True,
        )
        grams = st.number_input(
            "Grams", min_value=1.0, max_value=2000.0,
            value=float(st.session_state.log_grams), step=1.0,
            label_visibility="collapsed", key="grams_input",
        )
        st.session_state.log_grams = grams

        # Portion chips
        if portions:
            st.markdown(
                f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
                f"color:{MUTED};letter-spacing:0.6px;margin:8px 0 4px;'>"
                f"QUICK FILL</div>",
                unsafe_allow_html=True,
            )
            chip_cols = st.columns(min(len(portions), 4))
            for i, p in enumerate(portions[:4]):
                if chip_cols[i].button(p["label"], key=f"chip_{i}"):
                    st.session_state.log_grams = p["grams"]
                    st.rerun()

        # Meal type pills
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;"
            f"margin:1rem 0 4px;'>Meal</div>",
            unsafe_allow_html=True,
        )
        meal_cols = st.columns(4)
        for col, mt in zip(meal_cols, MEAL_TYPES):
            is_sel = st.session_state.log_meal_type == mt
            label = MEAL_LABELS[mt]
            if col.button(
                label,
                key=f"meal_pill_{mt}",
                type="primary" if is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state.log_meal_type = mt
                st.rerun()

        # Scaled nutrition preview
        scaled = scale_nutrients(nutrients_100g, grams)
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:10px;"
            f"color:{MUTED};letter-spacing:0.8px;text-transform:uppercase;"
            f"margin:1rem 0 4px;'>Nutrition · scaled to {grams:.0f}g</div>",
            unsafe_allow_html=True,
        )

        PREVIEW = [
            ("Energy",  "energy_kcal", "kcal", True),
            ("Protein", "protein_g",   "g",    False),
            ("Fat",     "fat_g",       "g",    False),
            ("Carbs",   "carb_g",      "g",    False),
        ]
        preview_html = ""
        for label, key, unit, bold in PREVIEW:
            val = scaled.get(key, 0)
            size = "16px" if bold else "14px"
            weight = "600" if bold else "400"
            preview_html += (
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:6px 0;border-bottom:1px solid {RULE};'>"
                f"<span style='font-family:Inter,sans-serif;font-size:13px;"
                f"color:{MUTED};'>{label}</span>"
                f"<span style='font-family:JetBrains Mono,monospace;font-size:{size};"
                f"font-weight:{weight};color:{INK};'>{val:.1f} {unit}</span>"
                f"</div>"
            )
        st.markdown(f"<div style='margin-bottom:1.25rem;'>{preview_html}</div>", unsafe_allow_html=True)

        # Add button
        meal_label = MEAL_LABELS[st.session_state.log_meal_type]
        if st.button(f"Add to {meal_label}", type="primary", use_container_width=True):
            entry = MealEntry(
                date=log_date,
                meal_type=st.session_state.log_meal_type,
                food_name=st.session_state.selected_food_name,
                grams=round(grams, 1),
                nutrients=scaled,
            )
            with get_session() as session:
                session.add(entry)
                session.commit()
            st.success(f"Added {st.session_state.selected_food_name} ({grams:.0f}g)")
            st.session_state.food_detail = {}
            st.session_state.selected_food_name = ""
            st.session_state.last_query = ""
            st.session_state.log_grams = 100.0
            st.rerun()
