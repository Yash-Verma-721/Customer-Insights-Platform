import streamlit as st

def show_login():

    if st.button("⬅ Back to Home"):
        st.session_state.page = "home"
        st.rerun()

    st.title("🔐 Login")

    username = st.text_input("Username")

    password = st.text_input(
        "Password",
        type="password"
    )

    st.button("Login")