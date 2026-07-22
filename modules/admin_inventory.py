import streamlit as st
import pandas as pd
from database.inventory_repository import get_marketplace_inventory_workflow
from utils.ui_helpers import render_header, render_empty_state

def _load_inventory_data():
    data = get_marketplace_inventory_workflow()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

def show_marketplace_inventory():
    render_header("Marketplace Inventory", "Comprehensive view of the marketplace inventory lifecycle.", "Marketplace Inventory")
    
    df = _load_inventory_data()
    
    if df.empty:
        st.info("No inventory data found in the marketplace.")
        return
        
    st.markdown("### Inventory Lifecycle Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", len(df))
    col2.metric("Total Available Units", df['Available Quantity'].sum())
    col3.metric("Total Reserved Units", df['Reserved Quantity'].sum())
    col4.metric("Out of Stock Items", len(df[df['Warehouse Status'] == 'Out of Stock']))
    
    st.markdown("### Marketplace Stock Status")
    
    # Display the rich enterprise-grade table
    st.dataframe(
        df[['Vendor', 'Product', 'Category', 'Available Quantity', 'Reserved Quantity', 'Warehouse Status', 'Stock Status', 'Last Procurement Date']],
        use_container_width=True,
        hide_index=True
    )
    
def show_procurement_workflow():
    render_header("Procurement Workflow", "Manage vendor stock procurement and marketplace replenishment.", "Procurement")
    
    df = _load_inventory_data()
    
    if df.empty:
        st.info("No procurement data found.")
        return
        
    st.markdown("### Procurement Status Overview")
    
    pending_reorder = df[df['Procurement Status'] == 'Pending Reorder']
    procured = df[df['Procurement Status'] == 'Procured']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Items Pending Reorder", len(pending_reorder))
    col2.metric("Procured Items", len(procured))
    col3.metric("Total Received Quantity", df['Received Quantity'].sum())
    
    st.markdown("### Active Procurement Queue")
    
    if not pending_reorder.empty:
        st.warning(f"{len(pending_reorder)} products require procurement from vendors.")
        st.dataframe(
            pending_reorder[['Vendor', 'Product', 'Procurement Status', 'Ordered Quantity', 'Received Quantity', 'Available Quantity', 'Stock Status']],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("All products have adequate stock. No pending procurements.")
        
    st.markdown("### Completed Procurements")
    st.dataframe(
        procured[['Vendor', 'Product', 'Procurement Status', 'Received Quantity', 'Available Quantity', 'Last Procurement Date']],
        use_container_width=True,
        hide_index=True
    )
