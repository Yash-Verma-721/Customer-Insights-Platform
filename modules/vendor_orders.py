import streamlit as st
import pandas as pd
from services.order_service import fetch_vendor_order_items, change_order_item_status
from core.exceptions import AppError, AuthorizationError
from config.order_status import VendorOrderStatus
from utils.ui_helpers import render_header

def show_vendor_orders():
    render_header("Vendor Orders", "Manage the fulfillment status of your marketplace items.", "Orders")
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User session not found. Please log in.")
        return
        
    order_items = fetch_vendor_order_items(user_id)
    
    if not order_items:
        st.info("You do not have any orders yet.")
        return
        
    df = pd.DataFrame(order_items)
    
    # KPIs
    st.markdown("### Overview")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Items", len(df))
    with kpi2:
        pending = len(df[df['item_status'] == VendorOrderStatus.PENDING])
        st.metric("Pending", pending)
    with kpi3:
        delivered = len(df[df['item_status'] == VendorOrderStatus.DELIVERED])
        st.metric("Delivered", delivered)
    with kpi4:
        cancelled = len(df[df['item_status'] == VendorOrderStatus.CANCELLED])
        st.metric("Cancelled", cancelled)
        
    st.divider()
    
    # Search & Filter
    col_search, col_filter = st.columns(2)
    with col_search:
        search_id = st.text_input("Search by Order Code")
    with col_filter:
        status_filter = st.multiselect("Filter by Item Status", VendorOrderStatus.all_statuses(), default=[])
        
    filtered_df = df.copy()
    if search_id:
        filtered_df = filtered_df[filtered_df['order_code'].str.contains(search_id, case=False, na=False)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['item_status'].isin(status_filter)]
        
    st.markdown("### Order Items")
    
    # Display table
    display_df = filtered_df[['order_item_id', 'order_code', 'order_date', 'customer_name', 
                              'product_name', 'quantity', 'total_amount', 'item_status', 'status_updated_at']]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.markdown("### Update Fulfillment Status")
    
    # Filter only items that can be transitioned (not cancelled, refunded, etc. unless needed)
    updatable_items = df[~df['item_status'].isin([VendorOrderStatus.CANCELLED, VendorOrderStatus.REFUNDED])]
    
    if updatable_items.empty:
        st.info("No active items available for status update.")
        return
        
    with st.form("update_status_form"):
        c1, c2 = st.columns(2)
        with c1:
            options = []
            for _, row in updatable_items.iterrows():
                options.append(f"{row['order_item_id']} - {row['product_name']} ({row['item_status']})")
                
            selected_option = st.selectbox("Select Order Item", options)
        with c2:
            new_status = st.selectbox("New Status", VendorOrderStatus.all_statuses())
            
        submitted = st.form_submit_button("Update Status")
        if submitted:
            if selected_option:
                item_id = int(selected_option.split(" - ")[0])
                old_status = updatable_items[updatable_items['order_item_id'] == item_id]['item_status'].values[0]
                
                try:
                    change_order_item_status(user_id, item_id, old_status, new_status)
                    st.success(f"Item #{item_id} successfully updated to {new_status}!")
                    st.rerun()
                except AppError as e:
                    st.error(str(e))
                except AuthorizationError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")
