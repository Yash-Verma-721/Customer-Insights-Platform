import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, build_sales_profile, money, percent
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=t, b=b))
    return fig

def show_sales_analytics():
    render_header("Sales Analytics", "Analyze revenue trends, purchase values, and sales performance.", "Sales Analytics")

    df, source_label, source_name = get_analytics_df("sales")
    render_data_source_banner(source_label, source_name)

    if df is None or df.empty:
        render_empty_state()
        render_footer("Sales Analytics")
        return
    with branded_spinner("Loading sales analytics..."):
        from utils.cache import get_cached_metric
        detected = get_cached_metric("detected_mp", detect_marketplace_columns, df)
        profile, metrics, columns = get_cached_metric("sales_profile", build_sales_profile, df, detected)

    # Computations for KPIs and Tables
    has_dates = metrics.get("has_date_column", False)
    avg_daily_sales = 0
    monthly_summary = pd.DataFrame()
    best_month = None
    worst_month = None
    forecast = None

    if has_dates and not profile.empty and "date" in profile.columns:
        profile_dates = pd.to_datetime(profile["date"], errors="coerce")
        unique_days = profile_dates.dt.date.nunique()
        avg_daily_sales = metrics.get("total_sales", 0) / unique_days if unique_days > 0 else 0
        
        # Monthly Aggregations
        profile_dates_period = profile_dates.dt.to_period("M").astype(str)
        monthly_summary = profile.groupby(profile_dates_period).agg(
            Revenue=("revenue", "sum"),
            Orders=("order", "nunique")
        ).reset_index().rename(columns={"date": "Month"})
        
        monthly_summary = monthly_summary.sort_values("Month")
        if not monthly_summary.empty:
            best_month = monthly_summary.loc[monthly_summary["Revenue"].idxmax()]
            worst_month = monthly_summary.loc[monthly_summary["Revenue"].idxmin()]

    # 1. Executive KPIs
    st.markdown("### Executive KPIs")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue", money(metrics.get("total_sales", 0)))
    k2.metric("Total Orders", f"{metrics.get('total_orders', 0):,}")
    k3.metric("Avg Order Value", money(metrics.get("avg_order_value", 0)))
    k4.metric("Avg Daily Sales", money(avg_daily_sales))
    k5.metric("Growth %", percent(metrics.get("growth_pct", 0)))
    
    # 2. Charts
    st.markdown("### Sales Charts")
    if has_dates and not monthly_summary.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig_rev = px.line(monthly_summary, x="Month", y="Revenue", markers=True, title="Revenue Trend")
            st.plotly_chart(_apply_chart_layout(fig_rev, height=350), use_container_width=True)
            
            fig_ord = px.line(monthly_summary, x="Month", y="Orders", markers=True, title="Order Trend")
            st.plotly_chart(_apply_chart_layout(fig_ord, height=350), use_container_width=True)
        with c2:
            fig_bar = px.bar(monthly_summary, x="Month", y="Revenue", text_auto=".2s", title="Monthly Sales Volume")
            st.plotly_chart(_apply_chart_layout(fig_bar, height=350), use_container_width=True)
            
            top_periods = monthly_summary.sort_values("Revenue", ascending=False).head(5)
            fig_top = px.bar(top_periods, x="Month", y="Revenue", title="Top Sales Periods")
            st.plotly_chart(_apply_chart_layout(fig_top, height=350), use_container_width=True)
    else:
        st.info("Date column was not detected, so timeline analysis is unavailable.")
        if columns.get("revenue"):
            st.plotly_chart(_apply_chart_layout(px.histogram(profile, x="revenue", nbins=30, title="Order Value Distribution"), height=420, t=45), use_container_width=True)
        else:
            st.warning("Revenue column was not detected. Add a sales, amount, revenue, or order value field for value analysis.")

    # 3. Insights
    st.markdown("### Insights")
    if has_dates and not monthly_summary.empty:
        st.info(f"**Best Month:** {best_month['Month']} with {money(best_month['Revenue'])} in revenue and {best_month['Orders']} orders.")
        st.info(f"**Worst Month:** {worst_month['Month']} with {money(worst_month['Revenue'])} in revenue and {worst_month['Orders']} orders.")
        if metrics.get("growth_pct", 0) > 0:
            st.success(f"**Growth Summary:** The platform is seeing a positive recent growth trend of {percent(metrics.get('growth_pct'))} compared to the previous period.")
        elif metrics.get("growth_pct", 0) < 0:
            st.warning(f"**Growth Summary:** The platform is seeing a recent decline of {percent(metrics.get('growth_pct'))} compared to the previous period. Intervention may be needed.")
        else:
            st.info("**Growth Summary:** Revenue growth has remained flat in the most recent period.")
            
        # ML Forecasting
        from utils.ml_models import ml_sales_forecast
        forecast = ml_sales_forecast(monthly_summary)
        
        if forecast.get("status") == "success":
            st.markdown("#### 🤖 AI Sales Forecast")
            f1, f2, f3 = st.columns(3)
            f1.metric("Predicted Next Period", money(forecast["forecast_revenue"]))
            f2.metric("Projected Trend", forecast["trend"])
            f3.metric("Model Confidence", forecast["confidence"])
            
            st.info(f"**AI Recommendation:** {forecast['recommendation']}")
    else:
        st.info("The monthly revenue trend indicates macro seasonality, while the monetary value distribution reveals how individual purchases are clustered.")

    # 4. Detailed Tables
    with st.expander("Detailed Sales Data"):
        if has_dates and not monthly_summary.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Monthly Summary**")
                st.dataframe(monthly_summary, use_container_width=True, hide_index=True)
            with c2:
                st.markdown("**Top Periods**")
                st.dataframe(monthly_summary.sort_values("Revenue", ascending=False).head(10), use_container_width=True, hide_index=True)
        else:
            st.dataframe(profile.head(100), use_container_width=True)
            
    st.markdown("---")
    st.markdown("### 📄 Module Report")
    if st.button("Generate Sales Report", type="primary"):
        with branded_spinner("Generating Sales Report..."):
            from modules.reports.sales_report import build_sales_report_blocks
            from modules.reports.report_utils import generate_excel_bytes
            
            # Include avg daily sales in metrics since it's computed here
            report_metrics = metrics.copy()
            report_metrics["avg_daily_sales"] = avg_daily_sales
            if best_month is not None:
                report_metrics["best_month"] = best_month['Month']
                report_metrics["worst_month"] = worst_month['Month']
                
            blocks = build_sales_report_blocks(report_metrics, forecast)
            st.session_state["sales_report_bytes"] = generate_excel_bytes(blocks, "Sales Report")
            
    if "sales_report_bytes" in st.session_state:
        st.download_button(
            label="Download Sales Report",
            data=st.session_state["sales_report_bytes"],
            file_name="sales_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary"
        )
        
    render_footer("Sales Analytics")
