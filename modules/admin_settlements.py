import streamlit as st
import pandas as pd
from database.connection import get_connection
from database.settlement_repository import get_all_settlements
from services.settlement_service import mark_settlement_paid
from utils.ui_helpers import render_header

def show_admin_settlements():
    render_header("Settlement Management", "Review vendor earnings and process payouts.", "Admin")
    
    admin_id = st.session_state.get("user_id")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        settlements = get_all_settlements(cursor)
    finally:
        conn.close()
        
    df = pd.DataFrame(settlements)
    
    if df.empty:
        st.info("No settlements found yet. Settlements are generated when orders are delivered.")
        return
        
    total_commission = df['commission_amount'].sum()
    pending = len(df[df['settlement_status'] == 'Pending'])
    paid = len(df[df['settlement_status'] == 'Paid'])
    
    # KPIs
    st.markdown("### Marketplace Financials")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Marketplace Commission", f"${total_commission:,.2f}")
    kpi2.metric("Pending Settlements", pending)
    kpi3.metric("Paid Settlements", paid)
    
    st.divider()
    
    # Search and Filter
    c_search, c_filter = st.columns(2)
    with c_search:
        search_q = st.text_input("Search by Vendor or Order Code")
    with c_filter:
        status_filter = st.multiselect("Filter by Status", ["Pending", "Paid"], default=["Pending"])
        
    filtered_df = df.copy()
    if search_q:
        filtered_df = filtered_df[
            filtered_df['vendor_name'].str.contains(search_q, case=False, na=False) | 
            filtered_df['order_code'].str.contains(search_q, case=False, na=False)
        ]
    if status_filter:
        filtered_df = filtered_df[filtered_df['settlement_status'].isin(status_filter)]
        
    st.markdown("### Settlement Queue")
    
    for idx, row in filtered_df.iterrows():
        with st.expander(f"Vendor: {row['vendor_name']} | Order: {row['order_code']} ({row['settlement_status']})"):
            st.markdown(f"""
            **Product:** {row['product_name']}
            
            **Gross Amount:** ${row['gross_amount']:.2f}
            **Marketplace Commission ({row['commission_rate']}%):** ${row['commission_amount']:.2f}
            **Net Payout to Vendor:** ${row['net_amount']:.2f}
            
            **Created At:** {row['created_at']}
            **Paid At:** {row['paid_at'] or 'Not Paid'}
            """)
            
            if row['settlement_status'] == "Pending":
                if st.button("Mark as Paid", key=f"pay_{row['id']}", type="primary"):
                    success, msg = mark_settlement_paid(admin_id, row['id'])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
