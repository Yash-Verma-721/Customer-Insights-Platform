import streamlit as st
import pandas as pd
from database.database import get_vendor_payments, process_vendor_payouts

def show_vendor_payments():
    st.markdown("<h2 style='color: #3b82f6;'>Payments & Settlements</h2>", unsafe_allow_html=True)
    st.markdown("Track your earnings, commissions, and payout history.")
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("User session not found.")
        return

    # Automatically process any pending payouts for this vendor/platform
    # In a real app this would be a background cron job, but here we can
    # run it silently to keep the data fresh.
    process_vendor_payouts()

    # Load Payments
    payments = get_vendor_payments(user_id)
    if not payments:
        st.info("No payment records found yet. Once you receive orders, your payouts will appear here.")
        return
        
    df = pd.DataFrame(payments)
    
    # Calculate Totals
    total_earnings = df['gross_amount'].sum()
    total_commission = df['commission_amount'].sum()
    total_net = df['net_payout'].sum()
    
    pending_df = df[df['status'] == 'Pending']
    settled_df = df[df['status'] == 'Settled']
    
    total_pending = pending_df['net_payout'].sum()
    total_settled = settled_df['net_payout'].sum()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Earnings", f"${total_earnings:,.2f}")
    with col2:
        st.metric("Total Commission", f"${total_commission:,.2f}")
    with col3:
        st.metric("Pending Payouts", f"${total_pending:,.2f}")
    with col4:
        st.metric("Settled Payouts", f"${total_settled:,.2f}")
        
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["⏳ Pending Settlements", "✅ Settled Payouts"])
    
    with tab1:
        if pending_df.empty:
            st.success("No pending payouts.")
        else:
            for _, row in pending_df.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns(4)
                    c1.write(f"**Order:** {row['order_code']}")
                    c2.write(f"Date: {row['order_date'][:10]}")
                    c3.write(f"Net: ${row['net_payout']:.2f}")
                    c4.write(f"Status: {row['status']}")
                    st.divider()
                    
    with tab2:
        if settled_df.empty:
            st.info("No settled payouts yet.")
        else:
            for _, row in settled_df.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns(4)
                    c1.write(f"**Order:** {row['order_code']}")
                    c2.write(f"Date: {row['order_date'][:10]}")
                    c3.write(f"Net: ${row['net_payout']:.2f}")
                    c4.write(f"Settled On: {row['settlement_date'][:10] if row['settlement_date'] else 'N/A'}")
                    st.divider()
