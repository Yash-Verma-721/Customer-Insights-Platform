import streamlit as st

from auth.auth_utils import (
    get_user,
    verify_password
)

def show_login():
    st.markdown('<div class="auth-glow-bg"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card-marker"></div>', unsafe_allow_html=True)
        
        if st.button("Back to Home", type="secondary"):
            st.session_state.page = "home"
            st.rerun()
            
        st.markdown("<h2 class='auth-title'>Welcome Back</h2>", unsafe_allow_html=True)
        st.markdown("<p class='auth-subtitle'>Secure access to your Customer Insights Platform.</p>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Login", use_container_width=True, type="primary"):
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
                st.session_state.user_id = user[0]
                st.session_state.username = user[2]
                st.session_state.full_name = user[1]
                st.session_state.role = user[6] if len(user) > 6 else "Manager"
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Incorrect password.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<hr style='border-top: 1px dashed #cbd5e1; margin: 15px 0;'>", unsafe_allow_html=True)
        
        if st.button("Become a Vendor", use_container_width=True, type="secondary"):
            st.session_state.page = "vendor_registration"
            st.rerun()
