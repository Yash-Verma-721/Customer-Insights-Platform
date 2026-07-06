import streamlit as st

from modules.signup import show_signup
from modules.login import show_login

st.set_page_config(
    page_title="Customer Insight Platform",
    page_icon="📊",
    layout="wide"
)

if "page" not in st.session_state:
    st.session_state.page = "home"




if st.session_state.page == "home":

    st.title("📊 Customer Insight Platform")

    st.write(
        "Turn your customer data into meaningful insights."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button("Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

    with col2:

        if st.button("Create Account", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()




elif st.session_state.page == "login":

    show_login()




elif st.session_state.page == "signup":

    show_signup()