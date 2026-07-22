import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=t, b=b))
    return fig

def _process_order_data(df, detected):
    status_col = detected.get("status", [None])[0] if detected.get("status") else None
    order_col = detected.get("order", [None])[0] if detected.get("order") else None
    date_col = detected.get("date", [None])[0] if detected.get("date") else None
    
    total_orders = df[order_col].nunique() if order_col else len(df)
    
    status_counts = {"Completed": 0, "Pending": 0, "Cancelled": 0, "Returned": 0}
    status_df = pd.DataFrame()
    daily_orders = pd.DataFrame()
    monthly_orders = pd.DataFrame()
    
    if status_col:
        s = df[status_col].astype(str).str.lower()
        completed = s.str.contains("success|complete|deliver|active|ship", na=False)
        returned = s.str.contains("return|refund", na=False)
        cancelled = s.str.contains("cancel|fail", na=False) & ~returned
        pending = s.str.contains("pending|process|wait|hold", na=False)
        
        status_counts["Completed"] = int(completed.sum())
        status_counts["Returned"] = int(returned.sum())
        status_counts["Cancelled"] = int(cancelled.sum())
        status_counts["Pending"] = int(pending.sum())
        
        # Calculate Others (unmatched)
        matched = completed | returned | cancelled | pending
        status_counts["Other/Unknown"] = int((~matched).sum())
        
        status_df = pd.DataFrame({
            "Status": list(status_counts.keys()),
            "Count": list(status_counts.values())
        })
        status_df = status_df[status_df["Count"] > 0]
        
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        df_valid = df[dates.notna()].copy()
        if not df_valid.empty:
            df_valid["_date"] = pd.to_datetime(df_valid[date_col]).dt.date
            df_valid["_month"] = pd.to_datetime(df_valid[date_col]).dt.to_period("M").astype(str)
            
            if order_col:
                daily_orders = df_valid.groupby("_date")[order_col].nunique().reset_index(name="Orders")
                monthly_orders = df_valid.groupby("_month")[order_col].nunique().reset_index(name="Orders")
            else:
                daily_orders = df_valid.groupby("_date").size().reset_index(name="Orders")
                monthly_orders = df_valid.groupby("_month").size().reset_index(name="Orders")
                
            daily_orders = daily_orders.rename(columns={"_date": "Date"}).sort_values("Date")
            monthly_orders = monthly_orders.rename(columns={"_month": "Month"}).sort_values("Month")

    return total_orders, status_counts, status_df, daily_orders, monthly_orders, status_col is not None, date_col is not None

def show_order_analytics():
    render_header("Order Analytics", "Analyze order fulfillment, return rates, and transaction volumes.", "Order Analytics")

    df, source_label, source_name = get_analytics_df("order")
    render_data_source_banner(source_label, source_name)

    if df is None or df.empty:
        render_empty_state()
        render_footer("Order Analytics")
        return
    with branded_spinner("Loading order analytics..."):
        from utils.cache import get_cached_metric
        detected = get_cached_metric("detected_ord", detect_marketplace_columns, df)
        total_orders, status_counts, status_df, daily_orders, monthly_orders, has_status, has_date = get_cached_metric(
            "order_profile", _process_order_data, df, detected
        )

    # 1. Executive KPIs
    st.markdown("### Executive KPIs")
    if not has_status:
        st.info("Awaiting order status fields in the active dataset.")
        
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Orders", f"{total_orders:,}")
    k2.metric("Completed", f"{status_counts['Completed']:,}" if has_status else "N/A")
    k3.metric("Pending", f"{status_counts['Pending']:,}" if has_status else "N/A")
    k4.metric("Cancelled", f"{status_counts['Cancelled']:,}" if has_status else "N/A")
    k5.metric("Returned", f"{status_counts['Returned']:,}" if has_status else "N/A")
    
    # 2. Charts
    st.markdown("### Order Volumes & Fulfillment")
    c1, c2 = st.columns(2)
    with c1:
        if has_status and not status_df.empty:
            fig_stat = px.pie(status_df, names="Status", values="Count", title="Order Status Breakdown")
            st.plotly_chart(_apply_chart_layout(fig_stat, height=350), use_container_width=True)
        else:
            st.info("No status data available for order breakdown chart.")
            
        if has_date and not daily_orders.empty:
            fig_daily = px.line(daily_orders, x="Date", y="Orders", title="Daily Orders Trend")
            st.plotly_chart(_apply_chart_layout(fig_daily, height=350), use_container_width=True)
        else:
            st.info("No date data available for daily timeline.")
            
    with c2:
        if has_status and not status_df.empty:
            fig_trend = px.bar(status_df.sort_values("Count", ascending=False), x="Status", y="Count", title="Fulfillment Trend", text_auto=".2s")
            st.plotly_chart(_apply_chart_layout(fig_trend, height=350), use_container_width=True)
        else:
            st.info("No status data available for fulfillment trend.")
            
        if has_date and not monthly_orders.empty:
            fig_month = px.bar(monthly_orders, x="Month", y="Orders", title="Monthly Orders Volume", text_auto=".2s")
            st.plotly_chart(_apply_chart_layout(fig_month, height=350), use_container_width=True)
        else:
            st.info("No date data available for monthly timeline.")
    
    # 3. Insights
    st.markdown("### Insights")
    if has_status:
        total_tracked = sum(status_counts.values())
        if total_tracked > 0:
            success_rate = (status_counts['Completed'] / total_tracked) * 100
            return_rate = (status_counts['Returned'] / total_tracked) * 100
            
            st.success(f"**Order Health:** The platform has a successful fulfillment rate of {success_rate:.1f}%.")
            st.info(f"**Fulfillment Summary:** There are currently {status_counts['Pending']} pending orders requiring processing.")
            
            if return_rate > 5.0:
                st.warning(f"**Return Analysis:** The return rate is {return_rate:.1f}%. Consider auditing product quality or shipping reliability.")
            else:
                st.success(f"**Return Analysis:** The return rate is healthy at {return_rate:.1f}%.")
    else:
        st.info("Order analytics isolate operational bottlenecks in fulfillment and highlight refund trends.")
    
    # 4. Detailed Tables
    with st.expander("Order Summary"):
        if has_date and not monthly_orders.empty:
            st.markdown("**Monthly Volume**")
            st.dataframe(monthly_orders.sort_values("Month", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.write("Detailed data unavailable.")
            
    st.markdown("---")
    st.markdown("### 📄 Module Report")
    
    if st.button("Generate Order Report", type="primary"):
        with branded_spinner("Generating Order Report..."):
            from modules.reports.order_report import build_order_report_blocks
            from modules.reports.report_utils import generate_excel_bytes
            
            return_rate = 0.0
            if has_status:
                total_tracked = sum(status_counts.values())
                if total_tracked > 0:
                    return_rate = (status_counts.get('Returned', 0) / total_tracked) * 100
                    
            blocks = build_order_report_blocks(total_orders, return_rate, status_df if has_status else pd.DataFrame())
            st.session_state["order_report_bytes"] = generate_excel_bytes(blocks, "Order Report")
            
    if "order_report_bytes" in st.session_state:
        st.download_button(
            label="Download Order Report",
            data=st.session_state["order_report_bytes"],
            file_name="order_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary"
        )
        
    render_footer("Order Analytics")
