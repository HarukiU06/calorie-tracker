import streamlit as st

from src.db.database import init_db
from src.ui.css import inject_css
from src.ui.sidebar import render_sidebar

st.set_page_config(page_title="Calorie Tracker", layout="wide")

init_db()
inject_css()
render_sidebar()

st.title("Calorie Tracker")
st.write("Select a page from the sidebar.")
