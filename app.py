import streamlit as st

from modules.signup import show_signup
from modules.login import show_login
from modules.upload import show_upload
from modules.cleaning import show_cleaning

from modules.user_management import show_user_management
from modules.library import show_library
from utils.ui_helpers import branded_spinner
from database.database import create_database, migrate_database
from config.roles import Roles
from config.navigation import render_navigation

APP_NAME = "Customer Insights Platform"

create_database()
migrate_database()

st.set_page_config(
    page_title=APP_NAME,
    page_icon="CA",
    layout="wide"
)

# ---------------- CUSTOM CSS ---------------- #
try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ---------------- SESSION ---------------- #

if "page" not in st.session_state:
    st.session_state.page = "home"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "activity_log" not in st.session_state:
    st.session_state.activity_log = []


# ---------------- HOME ---------------- #

if not st.session_state.logged_in:

    if st.session_state.page == "home":
        st.markdown(f"<div class='hero-title'>{APP_NAME}</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='hero-subtitle'>Analyze customer behavior, segments, revenue patterns, and retention "
            "opportunities with a modern Customer Insights Platform.</div>",
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

        with col2:
            if st.button("Login to Platform", use_container_width=True, type="primary"):
                st.session_state.page = "login"
                st.rerun()

        with col3:
            if st.button("Marketplace", use_container_width=True, type="secondary"):
                st.session_state.page = "marketplace"
                st.rerun()

        with col4:
            if st.button("Create Account", use_container_width=True):
                st.session_state.page = "signup"
                st.rerun()
                
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        # Add some feature highlights
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info("**Data Cleaning**\n\nAutomatically format, clean, and prepare your raw datasets for customer analysis.")
        with c2:
            st.info("**Segment Analysis**\n\nIdentify high-value customer groups and isolate key customer behaviors.")
        with c3:
            st.info("**Visual Analytics**\n\nGenerate interactive dashboards and export consolidated customer insights reports.")

    elif st.session_state.page == "signup":

        show_signup()

    elif st.session_state.page == "login":

        show_login()
        
    elif st.session_state.page == "marketplace":
        
        from modules.marketplace import show_marketplace
        show_marketplace()
        
    elif st.session_state.page == "checkout":
        
        from modules.checkout import show_checkout
        show_checkout()
        
    elif st.session_state.page == "vendor_registration":
        
        from modules.vendor_registration import show_vendor_registration
        show_vendor_registration()

else:
    import datetime
    import os
    import pandas as pd
    from database.database import get_dataset_metadata
    
    # ---------------- TOP NAVIGATION BAR ---------------- #
    # ---------------- TOP NAVIGATION BAR ---------------- #
    
    import streamlit.components.v1 as components
    components.html("""
        <script>
        setTimeout(() => {
            try {
                const input = window.parent.document.querySelector('input[placeholder="Global Search..."]');
                if (!input) {
                    fetch('http://localhost:9999', { method: 'POST', body: JSON.stringify([{tag: 'ERROR', className: 'Input not found'}])});
                    return;
                }
                let current = input;
                let data = [];
                while (current && current.tagName !== 'HTML') {
                    const style = window.parent.getComputedStyle(current);
                    data.push({
                        tag: current.tagName,
                        className: current.className,
                        testId: current.getAttribute('data-testid') || '',
                        scrollHeight: current.scrollHeight,
                        clientHeight: current.clientHeight,
                        overflow: style.overflow + ' ' + style.overflowY,
                        position: style.position,
                        top: style.top
                    });
                    current = current.parentElement;
                }
                fetch('http://localhost:9999', { method: 'POST', body: JSON.stringify(data) });
            } catch(e) {
                fetch('http://localhost:9999', { method: 'POST', body: JSON.stringify([{tag: 'ERROR', className: e.toString()}])});
            }
        }, 1500);
        </script>
    """, height=0)

    col1, col2, col3, col4 = st.columns([2.5, 2.5, 0.5, 0.8])
    
    with col1:
        st.markdown("### Customer Insights Platform")
        st.caption("Marketplace Database • Live")
        
    with col2:
        st.text_input("Search", placeholder="Global Search...", label_visibility="collapsed")
        
    with col3:
        with st.popover("🔔"):
            st.markdown("**Notifications** (4 New)")
            st.warning("⚠️ Low Stock Alert: SKU-8921 is below minimum threshold. (2m ago)")
            st.info("📋 Procurement Pending: PO-2934 requires your approval. (1h ago)")
            st.success("🏢 New Vendor Registered: TechCorp Inc. completed onboarding. (3h ago)")
            st.success("💳 Payment Received: Invoice #INV-229 settled. (5h ago)")
            
    with col4:
        user_initial = st.session_state.full_name[0].upper() if 'full_name' in st.session_state else 'A'
        with st.popover(f"👤 {user_initial} ▾"):
            st.button("My Profile", use_container_width=True)
            st.button("Theme", use_container_width=True)
            st.button("Project Settings", use_container_width=True)
            st.button("Documentation", use_container_width=True)
            st.button("Logout", type="primary", use_container_width=True)
    
    
    st.sidebar.markdown("<h3 style='color: #3b82f6; text-align: center; margin-bottom: 10px;'>Customer Analytics</h3>", unsafe_allow_html=True)
    
    if "login_time" not in st.session_state:
        st.session_state.login_time = datetime.datetime.now().strftime("%H:%M")
        
    role = st.session_state.get("role", Roles.MANAGER)
    
    if role == Roles.VENDOR:
        from database.vendor_repository import get_vendor_profile
        vendor_profile = get_vendor_profile(st.session_state.user_id)
        vendor_status = vendor_profile.get("vendor_status", "Pending") if vendor_profile else "Pending"
        
        if vendor_status != "Approved":
            from modules.vendor_status_page import show_vendor_status_page
            show_vendor_status_page(vendor_status, vendor_profile)
            
            st.sidebar.markdown("<br>" * 10, unsafe_allow_html=True)
            if st.sidebar.button("Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.page = "home"
                st.rerun()
            st.stop()
            
    # ---------------- DATA SOURCE SELECTION ---------------- #
    # Future support: Allow switching between Marketplace Database and Uploaded Dataset.
    # For now, we do not automatically restore the previously uploaded dataset.
    # The dashboard starts in a clean state unless a user explicitly uploads a new file.

    dataset_name_raw = st.session_state.get("file_details", {}).get("name", "None")
    uploader_raw = st.session_state.get("file_details", {}).get("user", "Unknown")
    time_raw = st.session_state.get("file_details", {}).get("time", "Unknown")
    report_raw = st.session_state.get("file_details", {}).get("last_report")
    
    # Professional fallbacks
    ds_name = "No dataset loaded" if dataset_name_raw == "None" or not dataset_name_raw else dataset_name_raw
    ds_color = "#94a3b8" if ds_name == "No dataset loaded" else "#60a5fa"
    uploader = "—" if uploader_raw == "Unknown" else uploader_raw
    up_time = "—" if time_raw == "Unknown" else time_raw
    rep_time = "Not Available" if not report_raw else report_raw
    
    # Dynamically calculate rows, cols, and health based on the active dataframe in session
    if "df" in st.session_state and st.session_state["df"] is not None:
        rows = st.session_state["df"].shape[0]
        cols = st.session_state["df"].shape[1]
        from utils.ui_helpers import calculate_readiness_score
        health_raw = calculate_readiness_score(st.session_state["df"])
        
        size_str = f"{rows:,} Rows, {cols:,} Cols"
        health_str = f"{health_raw}/100"
        health_color = "#4ade80"
        status_str = "Ready"
    else:
        rows = st.session_state.get("file_details", {}).get("rows", 0)
        cols = st.session_state.get("file_details", {}).get("cols", 0)
        health_raw = st.session_state.get("file_details", {}).get("health", "N/A")
        
        if rows == 0 and cols == 0:
            size_str = "—"
            status_str = "Not Available"
        else:
            size_str = f"{rows:,} Rows, {cols:,} Cols"
            status_str = "Ready"
            
        health_str = "—" if health_raw == "N/A" else f"{health_raw}/100"
        health_color = "#94a3b8" if health_raw == "N/A" else "#4ade80"
    
    role_display = 'Analyst' if role == 'Business Analyst' else role
    with st.sidebar.container(border=True):
        st.markdown(f"### {st.session_state.full_name}")
        st.markdown(f"**Role:** {role_display}")
        st.markdown(f"**Session:** {st.session_state.login_time}")
        
        st.divider()
        st.markdown("#### Dataset Information")
        st.markdown(f"**Current:** {ds_name}")
        st.markdown(f"**Uploaded By:** {uploader}")
        st.markdown(f"**Time:** {up_time}")
        st.markdown(f"**Size:** {size_str}")
        st.markdown(f"**Health:** {health_str}")
        st.markdown(f"**Status:** {status_str}")
        
        st.divider()
        st.markdown("#### Last Report Generated")
        st.markdown(f"**Time:** {rep_time}")

    if "current_nav" not in st.session_state:
        st.session_state.current_nav = "Dataset Library" if role == Roles.MANAGER else "Dashboard"

    nav = st.session_state.current_nav
    
    render_navigation(role, nav)

    page = st.session_state.current_nav
    
    if page == "Dataset Library" and role == Roles.MANAGER:
        show_library()
    elif page == "Dashboard":
        if role == Roles.VENDOR:
            from modules.vendor_dashboard import show_vendor_dashboard; show_vendor_dashboard()
        else:
            from modules.dashboard import show_dashboard; show_dashboard()
    elif page == "Orders" and role == Roles.VENDOR:
        from modules.vendor_orders import show_vendor_orders; show_vendor_orders()
    elif page == "Products" and role == Roles.VENDOR:
        from modules.vendor_products import show_vendor_products; show_vendor_products()
    elif page == "Inventory" and role == Roles.VENDOR:
        from modules.vendor_inventory import show_vendor_inventory; show_vendor_inventory()
    elif page == "Payments" and role == Roles.VENDOR:
        from modules.vendor_payments import show_vendor_payments; show_vendor_payments()
    elif page == "Upload":
        show_upload()
    elif page == "Cleaning":
        show_cleaning()
    elif page == "Data Explorer":
        from modules.analysis import show_analysis; show_analysis()
        
    # Admin Operations
    elif page == "Vendor Management":
        from modules.admin_vendors import show_admin_vendors; show_admin_vendors()
    elif page == "Marketplace Inventory":
        from modules.admin_inventory import show_marketplace_inventory; show_marketplace_inventory()
    elif page == "Procurement":
        from modules.admin_inventory import show_procurement_workflow; show_procurement_workflow()
    elif page == "Admin Orders":
        from modules.analytics_order import show_order_analytics; show_order_analytics()
    elif page == "Customer Management":
        from modules.admin_customers import show_customer_management; show_customer_management()
    elif page == "User Management":
        show_user_management()
        
    # Admin Analytics
    elif page == "Sales Analytics":
        from modules.analytics_sales import show_sales_analytics; show_sales_analytics()
    elif page == "Revenue Analytics":
        from modules.analytics_payment import show_payment_analytics; show_payment_analytics()
    elif page == "Customer Analytics":
        from modules.analytics_customer import show_customer_analytics; show_customer_analytics()
    elif page == "Inventory Analytics":
        from modules.analytics_inventory import show_inventory_analytics; show_inventory_analytics()
    elif page == "Vendor Analytics":
        from modules.analytics_vendor import show_vendor_analytics; show_vendor_analytics()
    elif page == "Marketplace AI Insights":
        from modules.ai_insights import show_ai_insights; show_ai_insights()
    elif page == "Recommendation Engine":
        from modules.ai_insights import show_recommendation_engine; show_recommendation_engine()
        
    # Reports Center
    elif page in ["Marketplace Reports", "Admin Vendor Reports", "Financial Reports", "Reports"]:
        from modules.report_center import show_report_center; show_report_center()

    st.sidebar.markdown("<br>" * 10, unsafe_allow_html=True)

    from utils.ui_helpers import display_session_log
    with st.sidebar:
        display_session_log()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.page = "home"
        
        # Clear dataset-related variables
        keys_to_clear = ["df", "raw_df", "profile", "metrics", "detected_columns", "file_details", "is_cleaned"]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
                
        # Trigger reload
        st.rerun()
