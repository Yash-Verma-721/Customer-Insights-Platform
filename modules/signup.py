import streamlit as st
from auth.auth_utils import (
    create_user,
    username_exists,
    email_exists
)
def show_signup():

    if st.button("⬅ Back to Home"):
        st.session_state.page = "home"
        st.rerun()

    st.title("📝 Create New Account")

    st.write("Fill in the details below to create your account.")

    full_name = st.text_input("Full Name")
    username = st.text_input("Username")
    email = st.text_input("Email")

    password = st.text_input(
        "Password",
        type="password"
    )

    confirm_password = st.text_input(
        "Confirm Password",
        type="password"
    )

    create_account = st.button("Create Account")


    if create_account:

        if not full_name:
            st.error("Full Name is required.")

        elif not username:
            st.error("Username is required.")

        elif not email:
            st.error("Email is required.")

        elif not password:
            st.error("Password is required.")

        elif password != confirm_password:
            st.error("Passwords do not match.")

        else:

            if username_exists(username):

                st.error("Username already exists.")

            elif email_exists(email):

                st.error("Email already exists.")

            else:

                create_user(
                    full_name,
                    username,
                    email,
                    password
                )

                st.success("Account created successfully!")