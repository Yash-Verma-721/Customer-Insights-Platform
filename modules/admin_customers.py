import streamlit as st
import pandas as pd
from database.customer_repository import get_marketplace_customers
from utils.ui_helpers import render_header, render_empty_state

def show_customer_management():
    render_header("Customer Management", "Marketplace CRM and Customer Directory.", "Customer Management")
    
    data = get_marketplace_customers()
    
    if not data:
        st.info("No customers found in the marketplace database.")
        return
        
    df = pd.DataFrame(data)
    
    st.markdown("### Customer Directory Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", len(df))
    col2.metric("VIP Customers", len(df[df['Customer Status'] == 'VIP']))
    col3.metric("Total Marketplace Spend", f"${df['Total Spend'].sum():,.2f}")
    col4.metric("Total Marketplace Orders", df['Total Orders'].sum())
    
    st.markdown("### Customer CRM")
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )
    
    st.info("Customer Analytics (Segmentation, LTV, Churn) are available in the Analytics module.")
