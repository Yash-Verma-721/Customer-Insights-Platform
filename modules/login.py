import streamlit as st

from auth.auth_utils import (
    get_user,
    verify_password
)


def show_login():

    if st.button("⬅ Back"):
        st.session_state.page = "home"
        st.rerun()

    st.title("🔐 Login")

    username = st.text_input("Username")

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login", use_container_width=True):

        if username == "" or password == "":
            st.warning("Please enter username and password.")
            return

        user = get_user(username)

        if user is None:
            st.error("Username not found.")
            return

        stored_password = user[4]

        if verify_password(password, stored_password):

            st.session_state.logged_in = True
            st.session_state.username = user[2]
            st.session_state.full_name = user[1]

            st.success("Login Successful!")

            st.rerun()

        else:

            st.error("Incorrect password.")