import streamlit as st

from modules.signup import show_signup
from modules.login import show_login
from modules.upload import show_upload
from modules.cleaning import show_cleaning

st.set_page_config(
    page_title="Customer Insight Platform",
    page_icon="📊",
    layout="wide"
)

# ---------------- SESSION ---------------- #

if "page" not in st.session_state:
    st.session_state.page = "home"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ---------------- HOME ---------------- #

if not st.session_state.logged_in:

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

    elif st.session_state.page == "signup":

        show_signup()

    elif st.session_state.page == "login":

        show_login()

else:

    st.sidebar.success(
        f"Welcome, {st.session_state.full_name}"
    )


    page = st.sidebar.radio(

        "Navigation",

        [
            "Upload",
            "Cleaning"
        ]
    )

    if page == "Upload":

        show_upload()

    elif page == "Cleaning":

        show_cleaning()

    st.sidebar.markdown("<br>" * 18, unsafe_allow_html=True)

    if st.sidebar.button("Logout"):

        st.session_state.logged_in = False
        st.session_state.page = "home"

        st.rerun()