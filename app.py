import streamlit as st

from src.db.database import init_db

init_db()

st.set_page_config(
    page_title="Calorie Tracker",
    page_icon="🥗",
    layout="wide",
)

st.title("🥗 Calorie Tracker")
st.write("サイドバーからページを選択してください。")
