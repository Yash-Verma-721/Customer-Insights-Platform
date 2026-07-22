import streamlit as st
from database.database import get_vendor_profile, update_vendor_profile

def show_vendor_profile():
    st.markdown('<div class="auth-glow-bg"></div>', unsafe_allow_html=True)
    st.markdown("<h2 class='auth-title' style='text-align: left;'>Business Profile</h2>", unsafe_allow_html=True)
    st.markdown("<p class='auth-subtitle' style='text-align: left;'>Manage your vendor information.</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User session not found.")
        return

    # Load vendor data on first render
    if "vendor_data" not in st.session_state:
        profile = get_vendor_profile(user_id)
        if profile:
            st.session_state.vendor_data = profile
        else:
            st.error("Vendor profile not found for this user.")
            return

    data = st.session_state.vendor_data

    # UI Form
    with st.form("vendor_profile_form"):
        st.markdown("### General Information")
        col1, col2 = st.columns(2)
        with col1:
            business_name = st.text_input("Business Name", value=data.get("vendor_name", ""))
            phone_number = st.text_input("Phone Number", value=data.get("phone_number", "") or "")
        with col2:
            owner_name = st.text_input("Owner Name", value=data.get("owner_name", ""))
            gst_number = st.text_input("GST Number", value=data.get("gst_number", "") or "")

        st.markdown("### Location")
        address = st.text_input("Address", value=data.get("address", "") or "")
        col_city, col_state = st.columns(2)
        with col_city:
            city = st.text_input("City", value=data.get("city", "") or "")
        with col_state:
            state = st.text_input("State", value=data.get("state", "") or "")

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Save Changes", type="primary")

    if submitted:
        if not all([business_name, owner_name, phone_number, gst_number, address, city, state]):
            st.error("All fields are required.")
        else:
            success, msg = update_vendor_profile(
                user_id=user_id,
                vendor_name=business_name,
                owner_name=owner_name,
                phone_number=phone_number,
                gst_number=gst_number,
                address=address,
                city=city,
                state=state
            )
            if success:
                st.success(msg)
                # Refresh session state data
                st.session_state.vendor_data = get_vendor_profile(user_id)
                st.rerun()
            else:
                st.error(msg)
