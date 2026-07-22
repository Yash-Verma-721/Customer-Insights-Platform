import streamlit as st
from auth.auth_utils import register_vendor

def show_vendor_registration():
    st.markdown('<div class="auth-glow-bg"></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card-marker"></div>', unsafe_allow_html=True)
        
        if st.button("Back to Home", type="secondary"):
            st.session_state.page = "home"
            st.rerun()
            
        st.markdown("<h2 class='auth-title'>Vendor Registration</h2>", unsafe_allow_html=True)
        st.markdown("<p class='auth-subtitle'>Join the marketplace to start selling your products.</p>", unsafe_allow_html=True)
        
        with st.form("vendor_registration_form"):
            st.markdown("### Business Information")
            business_name = st.text_input("Business Name", placeholder="Enter your registered business name")
            owner_name = st.text_input("Owner Name", placeholder="e.g. Yash Verma")
            
            col_gst, col_phone = st.columns(2)
            with col_gst:
                gst_number = st.text_input("GST Number", placeholder="Enter GST Number")
            with col_phone:
                phone_number = st.text_input("Phone Number", placeholder="Enter contact number")
            
            st.markdown("### Location")
            address = st.text_input("Address", placeholder="Street address")
            col_city, col_state = st.columns(2)
            with col_city:
                city = st.text_input("City", placeholder="City")
            with col_state:
                state = st.text_input("State", placeholder="State")
                
            st.markdown("### Account Credentials")
            username = st.text_input("Username", placeholder="Choose a unique username")
            email = st.text_input("Email Address", placeholder="name@company.com")
            
            col_pwd1, col_pwd2 = st.columns(2)
            with col_pwd1:
                password = st.text_input("Password", type="password", placeholder="********")
            with col_pwd2:
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="********")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Register as Vendor", use_container_width=True, type="primary")

        if submitted:
            if not all([business_name, owner_name, username, email, password, confirm_password, phone_number, gst_number, address, city, state]):
                st.error("All fields are required. Please fill in all the information.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                # Call existing backend function
                # The backend function signature: register_vendor(full_name, username, email, password, vendor_name, category)
                success, message = register_vendor(
                    full_name=owner_name,
                    username=username,
                    email=email,
                    password=password,
                    vendor_name=business_name,
                    category="General",
                    phone_number=phone_number,
                    gst_number=gst_number,
                    address=address,
                    city=city,
                    state=state
                )
                
                if success:
                    st.success(message)
                    st.info("You can now login as a vendor.")
                    st.session_state.page = "login"
                    # Note: We do not rerun immediately so the user can read the success message,
                    # or we can rerun if desired. Following existing patterns:
                    st.rerun()
                else:
                    st.error(message)
