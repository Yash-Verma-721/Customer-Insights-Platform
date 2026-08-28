import streamlit as st
import pandas as pd
from database.customer_repository import get_marketplace_customers, VIP_ORDER_THRESHOLD, RETURNING_ORDER_THRESHOLD, AT_RISK_DAYS
from utils.ui_helpers import render_header, render_empty_state
from utils.customer_metrics import money, percent

def _style_status(val):
    if 'VIP' in str(val):
        return 'color: #E2B93B; border: 1px solid rgba(226, 185, 59, 0.3); background-color: rgba(226, 185, 59, 0.1); border-radius: 12px; font-weight: 600;'
    elif 'Loyalist' in str(val):
        return 'color: #00D2FF; border: 1px solid rgba(0, 210, 255, 0.3); background-color: rgba(0, 210, 255, 0.1); border-radius: 12px; font-weight: 600;'
    elif 'At Risk' in str(val):
        return 'color: #FF4B4B; border: 1px solid rgba(255, 75, 75, 0.3); background-color: rgba(255, 75, 75, 0.1); border-radius: 12px; font-weight: 600;'
    elif 'Needs Attention' in str(val):
        return 'color: #FF9F43; border: 1px solid rgba(255, 159, 67, 0.3); background-color: rgba(255, 159, 67, 0.1); border-radius: 12px; font-weight: 600;'
    return ''

def show_customer_management():
    render_header("Customer Management", "Marketplace CRM and Customer Directory.", "Customer Management")
    
    data = get_marketplace_customers()
    
    if not data:
        st.info("No customers found in the marketplace database.")
        return
        
    df = pd.DataFrame(data)
    
    # --- 1. Search & Filters ---
    st.markdown("### Search & Filter")
    f1, f2 = st.columns(2)
    with f1:
        search_term = st.text_input("Search (Name or Email)", "")
    with f2:
        status_filter = st.selectbox("Filter by Status", ["All", "VIP", "Loyalist", "At Risk", "Needs Attention"])
    
    filtered_df = df.copy()
    
    if search_term:
        search_lower = search_term.lower()
        mask = (filtered_df['Customer Name'].str.lower().str.contains(search_lower, na=False)) | \
               (filtered_df['Email'].str.lower().str.contains(search_lower, na=False))
        filtered_df = filtered_df[mask]
        
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df['Customer Status'] == status_filter]
    
    st.markdown("---")
    st.markdown("### Customer Directory Overview")
    
    # --- 2. Improve Executive KPI Section ---
    total_customers = len(filtered_df)
    total_spend = filtered_df['Total Spend'].sum() if total_customers > 0 else 0
    total_orders = filtered_df['Total Orders'].sum() if total_customers > 0 else 0
    
    avg_spend = total_spend / total_customers if total_customers > 0 else 0
    repeat_rate = len(filtered_df[filtered_df['Total Orders'] > 1]) / total_customers if total_customers > 0 else 0
    vip_count = len(filtered_df[filtered_df['Customer Status'] == 'VIP'])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", f"{total_customers:,}")
    col2.metric("VIP Customers", f"{vip_count:,}")
    col3.metric("Total Spend", money(total_spend))
    col4.metric("Total Orders", f"{total_orders:,}")
    
    # Additional KPIs
    ec1, ec2, ec3, ec4 = st.columns(4)
    ec1.metric("Active Customers", f"{total_customers:,}")
    ec2.metric("Repeat Purchase Rate", percent(repeat_rate))
    ec3.metric("Avg Customer Spend", money(avg_spend))
    
    st.markdown("### Customer CRM")
    
    # --- 3. Improve Customer Status Display ---
    if not filtered_df.empty:
        try:
            display_df = filtered_df.copy()
            def map_status(x):
                if x == "VIP": return "⭐ VIP"
                if x == "Loyalist": return "🏅 Loyalist"
                if x == "At Risk": return "🛡 At Risk"
                if x == "Needs Attention": return "⚠ Needs Attention"
                return x
                
            display_df['Customer Status'] = display_df['Customer Status'].apply(map_status)
            
            # Pandas styling
            if hasattr(display_df.style, 'map'):
                styled_df = display_df.style.map(_style_status, subset=['Customer Status'])
            else:
                styled_df = display_df.style.applymap(_style_status, subset=['Customer Status'])
                
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        except Exception as e:
            # Fallback if styling fails
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.info("No customers match the current filters.")
        
    st.markdown("---")
    
    st.markdown("### Customer Classification Criteria")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(
            f"""
            <div style="padding: 16px; border-radius: 8px; background-color: #1E1E1E; border: 1px solid #333; height: 100%;">
                <h4 style="margin-top:0; margin-bottom: 12px;"><span style="color: #E2B93B; border: 1px solid rgba(226, 185, 59, 0.3); background-color: rgba(226, 185, 59, 0.1); border-radius: 12px; padding: 4px 12px; font-size: 14px;">⭐ VIP</span></h4>
                <p style="color: #E0E0E0; font-size: 14px; margin-bottom: 8px;">More than <strong>{VIP_ORDER_THRESHOLD}</strong> orders.</p>
                <p style="color: #888; font-size: 13px; line-height: 1.4; margin-bottom: 0;">High-value customers driving significant revenue. Prioritize for retention.</p>
            </div>
            """, unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""
            <div style="padding: 16px; border-radius: 8px; background-color: #1E1E1E; border: 1px solid #333; height: 100%;">
                <h4 style="margin-top:0; margin-bottom: 12px;"><span style="color: #00D2FF; border: 1px solid rgba(0, 210, 255, 0.3); background-color: rgba(0, 210, 255, 0.1); border-radius: 12px; padding: 4px 12px; font-size: 14px;">🏅 Loyalist</span></h4>
                <p style="color: #E0E0E0; font-size: 14px; margin-bottom: 8px;">Between <strong>{RETURNING_ORDER_THRESHOLD + 1}</strong> and <strong>{VIP_ORDER_THRESHOLD}</strong> orders.</p>
                <p style="color: #888; font-size: 13px; line-height: 1.4; margin-bottom: 0;">Customers who purchase regularly. Good candidates for upsells.</p>
            </div>
            """, unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"""
            <div style="padding: 16px; border-radius: 8px; background-color: #1E1E1E; border: 1px solid #333; height: 100%;">
                <h4 style="margin-top:0; margin-bottom: 12px;"><span style="color: #FF4B4B; border: 1px solid rgba(255, 75, 75, 0.3); background-color: rgba(255, 75, 75, 0.1); border-radius: 12px; padding: 4px 12px; font-size: 14px;">🛡 At Risk</span></h4>
                <p style="color: #E0E0E0; font-size: 14px; margin-bottom: 8px;">No purchases in <strong>{AT_RISK_DAYS}</strong> days.</p>
                <p style="color: #888; font-size: 13px; line-height: 1.4; margin-bottom: 0;">Previously active customers showing churn risk. Needs re-engagement.</p>
            </div>
            """, unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"""
            <div style="padding: 16px; border-radius: 8px; background-color: #1E1E1E; border: 1px solid #333; height: 100%;">
                <h4 style="margin-top:0; margin-bottom: 12px;"><span style="color: #FF9F43; border: 1px solid rgba(255, 159, 67, 0.3); background-color: rgba(255, 159, 67, 0.1); border-radius: 12px; padding: 4px 12px; font-size: 14px;">⚠ Needs Attention</span></h4>
                <p style="color: #E0E0E0; font-size: 14px; margin-bottom: 8px;"><strong>{RETURNING_ORDER_THRESHOLD}</strong> order or fewer.</p>
                <p style="color: #888; font-size: 13px; line-height: 1.4; margin-bottom: 0;">Recently acquired users. Requires onboarding and initial campaigns.</p>
            </div>
            """, unsafe_allow_html=True
        )
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Customer Analytics (Segmentation, LTV, Churn) are available in the Analytics module.")
