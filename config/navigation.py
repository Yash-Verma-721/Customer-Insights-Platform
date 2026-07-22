import streamlit as st
from config.roles import Roles

def render_navigation(role, current_nav):
    def nav_btn(label, internal_state):
        if st.sidebar.button(label, use_container_width=True, type="primary" if current_nav == internal_state else "secondary"):
            st.session_state.current_nav = internal_state
            st.rerun()

    if role == Roles.VENDOR:
        st.sidebar.markdown("### 🏪 Vendor Portal")
        nav_btn("Dashboard", "Dashboard")
        nav_btn("Orders", "Orders")
        nav_btn("Products", "Products")
        nav_btn("Inventory Management", "Inventory")
        nav_btn("Payments", "Payments")
        nav_btn("Reports", "Reports")
    else:
        if role == Roles.MANAGER:
            nav_btn("Dataset Library", "Dataset Library")

        nav_btn("Dashboard", "Dashboard")
        
        if role in [Roles.ADMIN, Roles.ANALYST]:
            st.sidebar.markdown("### 📂 Data Workspace")
            nav_btn("Upload Dataset", "Upload")
            nav_btn("Data Cleaning", "Cleaning")
            nav_btn("Data Explorer", "Data Explorer")
            
            st.sidebar.markdown("### ⚙️ Operations")
            nav_btn("Vendor Management", "Vendor Management")
            nav_btn("Marketplace Inventory", "Marketplace Inventory")
            nav_btn("Procurement", "Procurement")
            nav_btn("Orders", "Admin Orders")
            nav_btn("Customer Management", "Customer Management")
            
            st.sidebar.markdown("### 📊 Analytics")
            nav_btn("Sales Analytics", "Sales Analytics")
            nav_btn("Revenue Analytics", "Revenue Analytics")
            nav_btn("Customer Analytics", "Customer Analytics")
            nav_btn("Inventory Analytics", "Inventory Analytics")
            nav_btn("Marketplace AI Insights", "Marketplace AI Insights")
            nav_btn("Recommendation Engine", "Recommendation Engine")
            
        if role in [Roles.ADMIN, Roles.ANALYST, Roles.MANAGER]:
            st.sidebar.markdown("### 📑 Reports")
            nav_btn("Marketplace Reports", "Marketplace Reports")
            nav_btn("Vendor Reports", "Admin Vendor Reports")
            nav_btn("Financial Reports", "Financial Reports")

# End of navigation
