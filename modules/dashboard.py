import streamlit as st
import pandas as pd

from utils.customer_metrics import (
    build_customer_profile,
    build_vendor_profile,
    build_inventory_profile,
    build_sales_profile,
    build_recommendations,
    detect_customer_columns,
    detect_marketplace_columns,
    money,
    percent,
)
from modules.analytics_order import _process_order_data
from modules.analytics_payment import _process_payment_data
from utils.ui_helpers import (
    render_empty_state,
    render_footer,
    render_header,
    render_help_expander,
    branded_spinner,
)

def show_dashboard():
    render_header(
        "Executive Dashboard",
        "Executive view of business health, value, behavior, and next actions.",
        "Executive Dashboard",
    )

    role = st.session_state.get('role', 'Manager')
    st.subheader(f"Welcome back, {st.session_state.get('full_name', 'Analyst')} - {'Analyst' if role == 'Business Analyst' else role}")
    
    from utils.data_source_helper import get_analytics_df, render_data_source_banner
    df, source_label, source_name = get_analytics_df("marketplace")
    render_data_source_banner(source_label, source_name)
    
    if df is None or df.empty:
        render_empty_state("No dataset found. Import data to view the analytics overview.")
        render_footer("Executive Dashboard")
        return
    with branded_spinner("Loading dashboard metrics..."):
        from utils.cache import get_cached_metric
        detected_cust = get_cached_metric("detected", detect_customer_columns, df)
        detected_mp = get_cached_metric("detected_mp", detect_marketplace_columns, df)
        
        _, cust_metrics, _ = get_cached_metric("profile", build_customer_profile, df, detected_cust)
        _, vendor_metrics, _ = get_cached_metric("vendor_profile", build_vendor_profile, df, detected_mp)
        _, inv_metrics, _ = get_cached_metric("inv_profile", build_inventory_profile, df, detected_mp)
        _, sales_metrics, _ = get_cached_metric("sales_profile", build_sales_profile, df, detected_mp)
        
        total_orders, order_status_counts, _, _, _, has_status, _ = get_cached_metric("order_profile", _process_order_data, df, detected_mp)
        payment_metrics = get_cached_metric("payment_profile", _process_payment_data, df, detected_mp)
        
        recs, _ = get_cached_metric("dashboard_recs", build_recommendations, df, detected_mp)
        
    # Calculate Approval Rate and Settlement KPIs from Database
    approval_rate = 0.0
    total_commission = 0.0
    pending_settlements = 0
    paid_settlements = 0
    from database.connection import get_connection
    from database.vendor_repository import get_all_vendors_admin
    from database.settlement_repository import get_all_settlements
    conn = get_connection()
    try:
        cursor = conn.cursor()
        all_vendors = get_all_vendors_admin(cursor)
        if all_vendors:
            approved_count = sum(1 for v in all_vendors if v.get("vendor_status") == "Approved")
            approval_rate = (approved_count / len(all_vendors)) * 100
            
        all_settlements = get_all_settlements(cursor)
        if all_settlements:
            for s in all_settlements:
                total_commission += s.get("commission_amount", 0)
                if s.get("settlement_status") == "Pending":
                    pending_settlements += 1
                elif s.get("settlement_status") == "Paid":
                    paid_settlements += 1
    except Exception:
        pass
    finally:
        conn.close()
        
    st.markdown("### Executive KPIs")
    try:
        cont_exec = st.container(border=True)
    except TypeError:
        cont_exec = st.container()
        
    with cont_exec:
        col1, col2, col3 = st.columns(3)
        col1.metric("Revenue", money(sales_metrics.get("total_sales", 0)))
        col2.metric("Orders", f"{total_orders:,}")
        col3.metric("Customers", f"{cust_metrics.get('total_customers', 0):,}")
        
        col4, col5, col6, col7 = st.columns(4)
        col4.metric("Vendors", f"{vendor_metrics.get('total_vendors', 0):,}")
        col5.metric("Products", f"{inv_metrics.get('total_products', 0):,}")
        col6.metric("Inventory Value", money(inv_metrics.get("inventory_value", 0)))
        col7.metric("Approval Rate", f"{approval_rate:.1f}%")
        
        col8, col9, col10 = st.columns(3)
        col8.metric("Marketplace Commission", money(total_commission))
        col9.metric("Pending Settlements", pending_settlements)
        col10.metric("Paid Settlements", paid_settlements)

    st.markdown("### Executive Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown("**Sales**")
        st.write(f"Growth: {percent(sales_metrics.get('growth_pct', 0))}")
        st.write(f"AOV: {money(sales_metrics.get('avg_order_value', 0))}")
    with c2:
        st.markdown("**Customer**")
        st.write(f"Repeat Rate: {percent(cust_metrics.get('repeat_rate', 0))}")
    with c3:
        st.markdown("**Vendor**")
        st.write(f"Active: {vendor_metrics.get('total_vendors', 0)}")
    with c4:
        st.markdown("**Inventory**")
        st.write(f"Value: {money(inv_metrics.get('inventory_value', 0))}")
    with c5:
        st.markdown("**Payment**")
        st.write(f"Success Rate: {percent(payment_metrics.get('success_rate', 0))}")

    st.markdown("### Alerts")
    alert_triggered = False
    
    if inv_metrics.get("low_stock_count", 0) > 0:
        st.warning(f"📦 **Low Stock:** {inv_metrics['low_stock_count']} items are running low on inventory.")
        alert_triggered = True
        
    if has_status:
        total = sum(order_status_counts.values())
        if total > 0:
            ret_rate = (order_status_counts.get("Returned", 0) / total) * 100
            if ret_rate > 5.0:
                st.error(f"🔄 **High Returns:** Return rate is currently {ret_rate:.1f}%.")
                alert_triggered = True
                
    if payment_metrics.get("failed_count", 0) > 0:
        st.error(f"💳 **Failed Payments:** {payment_metrics['failed_count']} transactions have failed processing.")
        alert_triggered = True
        
    ml_clusters = st.session_state.get("ml_customer_clusters")
    if ml_clusters is not None and "ml_segment" in ml_clusters.columns:
        at_risk = len(ml_clusters[ml_clusters["ml_segment"].astype(str).str.contains("At Risk", na=False)])
        if at_risk > 0:
            st.warning(f"⚠️ **At Risk Customers:** {at_risk} customers are at high risk of churning.")
            alert_triggered = True
            
    if not alert_triggered:
        st.success("✅ No critical alerts at this time. All systems nominal.")

    st.markdown("### Top Performers")
    top_vendor = vendor_metrics.get("top_vendor_by_revenue", "N/A")
    
    top_products_dict = inv_metrics.get("top_products", {})
    top_product = list(top_products_dict.keys())[0] if top_products_dict else "N/A"
    
    top_cats_dict = inv_metrics.get("top_categories", {})
    best_category = list(top_cats_dict.keys())[0] if top_cats_dict else "N/A"
    
    p1, p2, p3 = st.columns(3)
    p1.info(f"**Top Vendor:**\n\n{top_vendor}")
    p2.info(f"**Top Product:**\n\n{top_product}")
    p3.info(f"**Best Category:**\n\n{best_category}")

    st.markdown("### 🤖 AI Highlights")
    if ml_clusters is not None:
        summary = st.session_state.get("ml_customer_summary")
        if summary is not None and not summary.empty:
            st.success("**ML Segmentation Active:** The customer base has been dynamically segmented. Check the Customer Analytics module for deeper insights.")
            
    if not recs:
        st.info("No sufficient data patterns detected to generate specific recommendations at this time.")
    else:
        top_recs = sorted(recs, key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x.get("priority", "Low"), 3))
        for rec in top_recs[:5]:
            priority = rec.get("priority", "Low")
            msg = f"**{rec.get('title', 'Insight')}** — {rec.get('message', '')} *(Action: {rec.get('action', '')})*"
            if priority == "High":
                st.error(msg)
            elif priority == "Medium":
                st.warning(msg)
            else:
                st.success(msg)

    render_footer("Executive Dashboard")
