import streamlit as st
from auth.auth_utils import (
    create_user,
    username_exists,
    email_exists
)

def show_signup():
    st.markdown('<div class="auth-glow-bg"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card-marker"></div>', unsafe_allow_html=True)
        
        if st.button("Back to Home", type="secondary"):
            st.session_state.page = "home"
            st.rerun()
            
        st.markdown("<h2 class='auth-title'>Create an Account</h2>", unsafe_allow_html=True)
        st.markdown("<p class='auth-subtitle'>Join to access enterprise-grade customer intelligence.</p>", unsafe_allow_html=True)
        
        full_name = st.text_input("Full Name", placeholder="e.g. Yash Verma")
        username = st.text_input("Username", placeholder="Choose a unique username")
        email = st.text_input("Email Address", placeholder="name@company.com")
        
        col_pwd1, col_pwd2 = st.columns(2)
        with col_pwd1:
            password = st.text_input("Password", type="password", placeholder="********")
        with col_pwd2:
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="********")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        create_account = st.button("Create Account", use_container_width=True, type="primary")

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
                        password,
                        "Business Analyst"
                    )
                    st.success("Account created successfully!")
                    st.info("You can now login.")
                    st.session_state.page = "login"
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<hr style='border-top: 1px dashed #cbd5e1; margin: 15px 0;'>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #475569; font-size: 14px;'>Already want to sell products?</p>", unsafe_allow_html=True)
        
        if st.button("Register as Vendor", use_container_width=True, type="secondary"):
            st.session_state.page = "vendor_registration"
            st.rerun()
