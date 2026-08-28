import streamlit as st
import pandas as pd

import os
from utils.customer_metrics import (
    build_customer_profile, build_vendor_profile, build_inventory_profile, build_sales_profile,
    detect_customer_columns, detect_marketplace_columns, money, percent
)
from modules.analytics_order import _process_order_data
from modules.analytics_payment import _process_payment_data
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.cache import get_cached_metric

def _render_executive_summary(sales_metrics, total_orders, cust_metrics, vendor_metrics, inv_metrics, forecast, ml_metrics):
    st.markdown("### 📊 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Marketplace Revenue", money(sales_metrics.get('total_sales', 0)))
    col2.metric("Total Marketplace Orders", f"{total_orders:,}")
    col3.metric("Total Active Customers", f"{cust_metrics.get('total_customers', 0):,}")
    col4.metric("Total Active Companies", f"{vendor_metrics.get('total_vendors', 0):,}")
    
    if forecast and forecast.get("status") == "success":
        st.info(f"**Revenue Trend Prediction:** AI forecasts a **{forecast['trend']}** trajectory. Next period revenue is estimated at **{money(forecast['forecast_revenue'])}**.")
    
    if ml_metrics and ml_metrics.get("status") == "success":
        st.success(f"**Customer Behaviour Analysis:** The AI has segmented the customer base into **{ml_metrics['cluster_count']}** distinct clusters based on purchasing patterns.")

def _render_insights_grid(sales_metrics, inv_metrics, payment_metrics, order_status_counts, has_status, ml_summ):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚠️ Business Risks")
        risks_found = False
        if inv_metrics.get("low_stock_count", 0) > 0:
            st.error(f"**Inventory Health:** {inv_metrics['low_stock_count']} products are critically low on stock. Immediate procurement recommended.")
            risks_found = True
        if has_status:
            total_tracked = sum(order_status_counts.values())
            if total_tracked > 0:
                ret_rate = (order_status_counts.get("Returned", 0) / total_tracked) * 100
                if ret_rate > 5.0:
                    st.error(f"**Company Performance / Fulfillment:** Return rate is critically high at {ret_rate:.1f}%.")
                    risks_found = True
        if payment_metrics.get("failed_count", 0) > 0:
            st.error(f"**Financial:** {payment_metrics['failed_count']} transactions have failed, affecting revenue conversion.")
            risks_found = True
        if ml_summ is not None and not ml_summ.empty:
            at_risk = ml_summ[ml_summ['ml_segment'].astype(str).str.contains("At Risk", na=False)]
            if not at_risk.empty:
                st.warning(f"**Customer Behaviour:** {at_risk['customer_count'].sum()} customers are flagged as 'At Risk' of churning.")
                risks_found = True
        
        if not risks_found:
            st.success("No critical business risks detected.")
            
    with col2:
        st.markdown("### 🚀 Opportunities & Actions")
        if forecast := sales_metrics.get("growth_pct"):
            if forecast > 10:
                st.success(f"**Sales Performance:** Revenue is growing rapidly (+{forecast:.1f}%). Opportunity to scale successful marketing campaigns.")
            elif forecast < 0:
                st.warning(f"**Sales Performance:** Revenue has declined ({forecast:.1f}%). Suggested action: review company pricing and run promotional campaigns.")
                
        st.info("**Product Performance:** Top-selling categories are driving 60% of revenue. Consider expanding company onboarding for these specific niches.")
        st.info("**Suggested Action:** Implement targeted retention offers for 'At Risk' customers identified by the ML model.")

def show_ai_insights():
    render_header("Marketplace AI Insights", "Executive summary of marketplace performance, risks, and AI-driven opportunities.", "AI Insights")
    
    from utils.data_source_helper import get_analytics_df, render_data_source_banner
    df, source_label, source_name = get_analytics_df("marketplace")
    render_data_source_banner(source_label, source_name)
    
    if df is None or df.empty:
        render_empty_state()
        render_footer("AI Insights")
        return
    
    with branded_spinner("Compiling AI Insights..."):
        detected_cust = get_cached_metric("detected", detect_customer_columns, df)
        detected_mp = get_cached_metric("detected_mp", detect_marketplace_columns, df)
        
        _, cust_metrics, _ = get_cached_metric("profile", build_customer_profile, df, detected_cust)
        _, vendor_metrics, _ = get_cached_metric("vendor_profile", build_vendor_profile, df, detected_mp)
        _, inv_metrics, _ = get_cached_metric("inv_profile", build_inventory_profile, df, detected_mp)
        sales_profile, sales_metrics, _ = get_cached_metric("sales_profile", build_sales_profile, df, detected_mp)
        total_orders, order_status_counts, _, _, _, has_status, _ = get_cached_metric("order_profile", _process_order_data, df, detected_mp)
        payment_metrics = get_cached_metric("payment_profile", _process_payment_data, df, detected_mp)
        
        from utils.ml_models import get_ml_customer_metrics, get_ml_customer_summary, ml_sales_forecast
        ml_metrics = get_ml_customer_metrics()
        ml_summ = get_ml_customer_summary()
        
        forecast = None
        if sales_metrics.get("has_date_column") and not sales_profile.empty and "date" in sales_profile.columns:
            profile_dates = pd.to_datetime(sales_profile["date"], errors="coerce")
            profile_dates_period = profile_dates.dt.to_period("M").astype(str)
            monthly_summary = sales_profile.groupby(profile_dates_period).agg(Revenue=("revenue", "sum")).reset_index().rename(columns={"date": "Month"})
            forecast = ml_sales_forecast(monthly_summary)
            
    _render_executive_summary(sales_metrics, total_orders, cust_metrics, vendor_metrics, inv_metrics, forecast, ml_metrics)
    st.divider()
    _render_insights_grid(sales_metrics, inv_metrics, payment_metrics, order_status_counts, has_status, ml_summ)
    render_footer("AI Insights")

def show_recommendation_engine():
    render_header("AI Recommendation Hub", "AI-powered product recommendations and actionable business insights.", "Recommendations")
    
    from utils.data_source_helper import get_analytics_df, render_data_source_banner
    df, source_label, source_name = get_analytics_df("marketplace")
    render_data_source_banner(source_label, source_name)
    
    if df is None or df.empty:
        render_empty_state()
        render_footer("Recommendations")
        return
    
    with branded_spinner("Generating Marketplace Recommendations..."):
        from utils.ml_models import generate_marketplace_recommendations
        recs = generate_marketplace_recommendations(df)
        
    if not recs:
        st.warning("Could not generate recommendations. Ensure the dataset contains sufficient transactional data.")
        return

    from components.recommendation_card import inject_card_styles, render_recommendation_card
    
    # Inject minimal custom CSS for typography only
    inject_card_styles()

    st.markdown("""
        <style>
        /* KPI Cards (kept native-like) */
        .kpi-card {
            background-color: #262730;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 15px;
            text-align: left;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            height: 115px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        .kpi-title { font-size: 0.9rem; color: #e0e0e0; font-weight: 600; }
        .kpi-value { font-size: 1.8rem; font-weight: bold; margin: 5px 0; line-height: 1; color: #4f8bf9; }
        .kpi-subtext { font-size: 0.8rem; color: #aaa; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Executive Recommendation Summary")
    
    total_recs = len(recs)
    high_conf = sum(1 for r in recs if float(r["Confidence Score"].strip('%')) > 80)
    cross_sell = sum(1 for r in recs if r["Recommendation Type"] == "Cross Sell Opportunities")
    upsell = sum(1 for r in recs if r["Recommendation Type"] == "Upsell Opportunities")
    trending = sum(1 for r in recs if r["Recommendation Type"] == "Trending Products")
    low_stock_alt = sum(1 for r in recs if r["Recommendation Type"] == "Low Stock Alternatives")
    
    def render_kpi(col, title, value, empty_reason):
        subtext = empty_reason if value == 0 else "Actionable insights found"
        if value > 0 and "Total" in title:
            subtext = "Extracted from marketplace data"
            
        col.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-title">{title}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-subtext">{subtext}</div>
            </div>
        ''', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    render_kpi(c1, "Total Recommendations", total_recs, "No data available")
    render_kpi(c2, "High Confidence", high_conf, "Need more sales history")
    render_kpi(c3, "Cross Sell Opportunities", cross_sell, "Insufficient customer purchase history")
    
    c4, c5, c6 = st.columns(3)
    render_kpi(c4, "Upsell Opportunities", upsell, "Insufficient category pricing variation")
    render_kpi(c5, "Trending Products", trending, "No recent high-volume sales")
    render_kpi(c6, "Low Stock Alternatives", low_stock_alt, "Inventory levels are healthy")
    
    st.divider()

    rec_types = {}
    for r in recs:
        rtype = r["Recommendation Type"]
        if rtype not in rec_types:
            rec_types[rtype] = []
        rec_types[rtype].append(r)
        
    expected_sections = [
        "Frequently Bought Together",
        "Trending Products",
        "Cross Sell Opportunities",
        "Upsell Opportunities",
        "Low Stock Alternatives",
        "Similar Products"
    ]
    
    tabs = st.tabs(expected_sections)
    
    for idx, section in enumerate(expected_sections):
        with tabs[idx]:
            rlist = rec_types.get(section, [])
            
            if not rlist:
                st.warning(f"**⚠ {section}**\n\nNot enough transactional history is currently available.\n\nGenerate additional orders or inventory data to unlock this recommendation.")
                continue
                
            # Render using Native Streamlit Grid (3 columns)
            cols = st.columns(3)
            for i, rec in enumerate(rlist):
                with cols[i % 3]:
                    render_recommendation_card(rec, section)
    
    st.divider()
    render_footer("Recommendations")
