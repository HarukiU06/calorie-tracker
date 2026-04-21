import streamlit as st

from src.db.database import init_db

st.set_page_config(page_title="Calorie Tracker", layout="wide")
init_db()

pg = st.navigation([
    st.Page("pages/1_Profile.py",   title="Profile",   url_path="profile"),
    st.Page("pages/2_Log_Meal.py",  title="Log Meal",  url_path="log-meal"),
    st.Page("pages/3_Dashboard.py", title="Dashboard", url_path="dashboard"),
])
pg.run()
