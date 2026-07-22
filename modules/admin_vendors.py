import streamlit as st
import pandas as pd
from database.connection import get_connection
from database.vendor_repository import get_all_vendors_admin
from services.vendor_service import process_vendor_approval
from utils.ui_helpers import render_header

def show_admin_vendors():
    render_header("Vendor Management", "Review and manage marketplace vendor applications.", "Admin")
    
    admin_id = st.session_state.get("user_id")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        vendors = get_all_vendors_admin(cursor)
    finally:
        conn.close()
        
    df = pd.DataFrame(vendors)
    
    if df.empty:
        st.info("No vendors found.")
        return
        
    pending = len(df[df['vendor_status'] == 'Pending'])
    approved = len(df[df['vendor_status'] == 'Approved'])
    suspended = len(df[df['vendor_status'] == 'Suspended'])
    
    # KPIs
    st.markdown("### Vendor Status Overview")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Pending Vendors", pending)
    kpi2.metric("Approved Vendors", approved)
    kpi3.metric("Suspended Vendors", suspended)
    
    st.divider()
    
    # Search and Filter
    c_search, c_filter = st.columns(2)
    with c_search:
        search_q = st.text_input("Search by Vendor Name or Email")
    with c_filter:
        status_filter = st.multiselect("Filter by Status", ["Pending", "Approved", "Rejected", "Suspended"], default=["Pending", "Approved", "Suspended"])
        
    filtered_df = df.copy()
    if search_q:
        filtered_df = filtered_df[filtered_df['vendor_name'].str.contains(search_q, case=False, na=False) | 
                                  filtered_df['user_email'].str.contains(search_q, case=False, na=False)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['vendor_status'].isin(status_filter)]
        
    st.markdown("### Vendor Directory")
    
    for idx, row in filtered_df.iterrows():
        with st.expander(f"{row['vendor_name']} ({row['vendor_status']}) - {row['user_email']}"):
            st.markdown(f"""
            **Owner:** {row['owner_name'] or 'N/A'} | **Phone:** {row['phone_number'] or 'N/A'} | **GST:** {row['gst_number'] or 'N/A'}
            
            **Address:** {row['address'] or 'N/A'}, {row['city'] or 'N/A'}, {row['state'] or 'N/A'}
            
            **Category:** {row['category'] or 'N/A'} | **Created:** {row['created_at']}
            """)
            
            status = row['vendor_status']
            vid = row['id']
            
            # Action Forms
            col_act1, col_act2 = st.columns(2)
            
            with col_act1:
                if status in ["Pending", "Suspended"]:
                    if st.button("Approve Vendor", key=f"app_{vid}", type="primary"):
                        success, msg = process_vendor_approval(admin_id, vid, "Approve")
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)
                        
            with col_act2:
                if status == "Pending":
                    with st.form(key=f"rej_form_{vid}"):
                        reason = st.text_input("Rejection Reason*")
                        if st.form_submit_button("Reject Vendor"):
                            success, msg = process_vendor_approval(admin_id, vid, "Reject", reason)
                            if success: st.success(msg); st.rerun()
                            else: st.error(msg)
                
                elif status == "Approved":
                    with st.form(key=f"susp_form_{vid}"):
                        reason = st.text_input("Suspension Reason*")
                        if st.form_submit_button("Suspend Vendor"):
                            success, msg = process_vendor_approval(admin_id, vid, "Suspend", reason)
                            if success: st.success(msg); st.rerun()
                            else: st.error(msg)
