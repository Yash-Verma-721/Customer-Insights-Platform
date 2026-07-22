import streamlit as st
from utils.ui_helpers import render_header

def show_vendor_status_page(status, profile):
    render_header("Vendor Application Status", "Review the current standing of your marketplace account.", "Status")
    
    if status == "Pending":
        st.warning("Your vendor application is currently **Pending Approval**.")
        st.info("Our marketplace administrators are reviewing your submitted details. You will receive an email once your account is activated. This usually takes 1-2 business days.")
    elif status == "Rejected":
        st.error("Your vendor application has been **Rejected**.")
        reason = profile.get("rejection_reason", "No reason provided.")
        st.markdown(f"**Reason for Rejection:** {reason}")
        st.info("If you believe this was a mistake, please contact marketplace support.")
    elif status == "Suspended":
        st.error("Your vendor account has been **Suspended**.")
        reason = profile.get("rejection_reason", "Violation of marketplace policies.")
        st.markdown(f"**Reason for Suspension:** {reason}")
        st.info("You currently cannot access your dashboard, manage products, or view orders. Please contact support to resolve this issue.")
    else:
        st.error(f"Unknown status: {status}")
