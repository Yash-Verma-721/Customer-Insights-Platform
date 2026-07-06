import streamlit as st

from modules.upload import show_upload
from modules.cleaning import show_cleaning

st.set_page_config(
    page_title="Customer Insight Platform",
    page_icon="📊",
    layout="wide"
)

page = st.sidebar.radio(
    "Development Menu",
    [
        "Upload",
        "Cleaning"
    ]
)

if page == "Upload":
    show_upload()

elif page == "Cleaning":
    show_cleaning()