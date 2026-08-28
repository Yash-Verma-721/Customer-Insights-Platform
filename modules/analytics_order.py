import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner
from utils.ui_components import (
    page_wrapper, page_header, section_header,
    kpi_card, info_card, render_metric_tile,
    bento_card, ranking_card, chart_container,
    render_page_header, render_section_header,
    render_kpi_card, render_info_card, render_ranking_list
)
from utils.ui_constants import *

def _apply_chart_layout(fig, height=320, t=15, b=15):
    fig.update_layout(height=height, margin=dict(l=15, r=15, t=t, b=b))
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
    with page_wrapper():
        df, source_label, source_name = get_analytics_df("order")

        # ---------------- Tier 1: Executive Header ---------------- #
        page_header(
            title="Order Analytics",
            subtitle=f"Active Dataset: {source_name or 'Order Fulfillment'} | Access Level: Executive",
            status="Nominal",
            status_type="success"
        )
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

        total_tracked = sum(status_counts.values()) if has_status else 0
        success_rate = (status_counts['Completed'] / total_tracked * 100) if total_tracked > 0 else 0.0
        return_rate = (status_counts['Returned'] / total_tracked * 100) if total_tracked > 0 else 0.0

        # ---------------- Tier 2: Quick KPI Grid ---------------- #
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            render_kpi_card(
                "Total Orders",
                f"{total_orders:,}",
                "Order Volume",
                "up",
                ICON_REPORT
            )

        with k2:
            render_kpi_card(
                "Completed Orders",
                f"{status_counts['Completed']:,}" if has_status else "N/A",
                "Fulfilled Orders",
                "up",
                ICON_SUCCESS
            )

        with k3:
            render_kpi_card(
                "Pending Orders",
                f"{status_counts['Pending']:,}" if has_status else "N/A",
                "Processing Queue",
                "up" if status_counts.get("Pending", 0) == 0 else "down",
                ICON_TIME
            )

        with k4:
            render_kpi_card(
                "Fulfillment Rate",
                f"{success_rate:.1f}%" if has_status else "N/A",
                "Fulfillment Margin",
                "up",
                ICON_TREND_UP
            )

        # ---------------- Tier 3: Primary Analytics Grid (Responsive 2:1 Bento Layout) ---------------- #
        if has_date and not daily_orders.empty:
            bento_left, bento_right = st.columns([2, 1])

            with bento_left:
                with chart_container("Daily Orders Trend", subtitle="Timeline trajectory of order processing volume"):
                    fig_daily = px.line(daily_orders, x="Date", y="Orders", title="Daily Orders Trend")
                    st.plotly_chart(_apply_chart_layout(fig_daily, height=320), use_container_width=True)

            with bento_right:
                with bento_card("Order Summary", ICON_REPORT):
                    if has_status:
                        render_metric_tile("Completed Orders", f"{status_counts['Completed']:,}")
                        render_metric_tile("Pending Orders", f"{status_counts['Pending']:,}")
                        render_metric_tile("Cancelled Orders", f"{status_counts['Cancelled']:,}")
                        render_metric_tile("Return Rate", f"{return_rate:.1f}%", return_rate)
                    else:
                        render_metric_tile("Total Orders Processed", f"{total_orders:,}")

                if has_date and not monthly_orders.empty:
                    best_month = monthly_orders.loc[monthly_orders["Orders"].idxmax()]
                    with bento_card("Performance Leaders", ICON_TREND_UP):
                        render_ranking_list([
                            {"name": f"{best_month['Month']}", "value": f"🥇 Peak Month ({best_month['Orders']:,} orders)"}
                        ])

            # ---------------- Tier 4: Secondary Analytics Grid (50% / 50%) ---------------- #
            sec1, sec2 = st.columns(2)

            with sec1:
                with chart_container("Order Status Breakdown", subtitle="Fulfillment ratio by order status"):
                    if has_status and not status_df.empty:
                        fig_stat = px.pie(status_df, names="Status", values="Count", title="Order Status Breakdown")
                        st.plotly_chart(_apply_chart_layout(fig_stat, height=320), use_container_width=True)
                    else:
                        st.info("No status data available for order breakdown chart.")

            with sec2:
                with chart_container("Monthly Orders Volume", subtitle="Monthly volume distribution"):
                    if has_date and not monthly_orders.empty:
                        fig_month = px.bar(monthly_orders, x="Month", y="Orders", title="Monthly Orders Volume", text_auto=".2s")
                        st.plotly_chart(_apply_chart_layout(fig_month, height=320), use_container_width=True)
                    else:
                        st.info("No date data available for monthly timeline.")

        else:
            with chart_container("Order Status & Volume Breakdown"):
                if has_status and not status_df.empty:
                    fig_stat = px.pie(status_df, names="Status", values="Count", title="Order Status Breakdown")
                    st.plotly_chart(_apply_chart_layout(fig_stat, height=380), use_container_width=True)
                else:
                    st.info("No timeline or status data available in the active dataset.")

        # ---------------- Tier 5: Order Intelligence & Recommendations ---------------- #
        section_header("Order Intelligence & AI Insights", subtitle="Fulfillment alerts, bottleneck signals, and operational recommendations")

        bot1, bot2 = st.columns(2)

        with bot1:
            with chart_container("Operational Fulfillment Intelligence"):
                if has_status:
                    render_info_card("Order Health", f"The platform has a successful fulfillment rate of {success_rate:.1f}%.", ICON_SUCCESS, "success")
                    
                    if status_counts['Pending'] > 0:
                        render_info_card("Processing Queue", f"There are currently {status_counts['Pending']:,} pending orders requiring processing.", ICON_TIME, "warning")

                    if return_rate > 5.0:
                        render_info_card("Return Analysis", f"The return rate is {return_rate:.1f}%. Consider auditing product quality or shipping reliability.", ICON_ALERT, "danger")
                    else:
                        render_info_card("Return Analysis", f"The return rate is healthy at {return_rate:.1f}%.", ICON_SUCCESS, "success")
                else:
                    render_info_card("Fulfillment Status", "Order analytics isolate operational bottlenecks in fulfillment and highlight refund trends.", ICON_INFO, "info")

        with bot2:
            with chart_container("AI Fulfillment Strategy"):
                if has_status and status_counts['Pending'] > 0:
                    render_info_card("Fulfillment Strategy", f"Prioritize clearance of the {status_counts['Pending']:,} pending orders to maintain customer satisfaction.", ICON_AI, "info")
                else:
                    render_info_card("Fulfillment Strategy", "All orders are fully processed. Operations nominal.", ICON_AI, "success")

                if return_rate > 5.0:
                    render_info_card("Quality Strategy", "Audit vendor packaging and delivery logistics for categories with return spikes.", ICON_AI, "warning")

        # ---------------- Detailed Order Data & Report Generator ---------------- #
        with chart_container("Detailed Order Data & Report Generator"):
            with st.expander("Order Volume Summary"):
                if has_date and not monthly_orders.empty:
                    st.markdown("**Monthly Volume Breakdown**")
                    st.dataframe(monthly_orders.sort_values("Month", ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.write("Detailed timeline data unavailable.")

            st.markdown("---")
            st.markdown("**📄 Generate Order Analytics Report**")
            if st.button("Generate Order Report", type="primary"):
                with branded_spinner("Generating Order Report..."):
                    from modules.reports.order_report import build_order_report_blocks
                    from modules.reports.report_utils import generate_excel_bytes

                    report_ret_rate = 0.0
                    if has_status and total_tracked > 0:
                        report_ret_rate = (status_counts.get('Returned', 0) / total_tracked) * 100

                    blocks = build_order_report_blocks(total_orders, report_ret_rate, status_df if has_status else pd.DataFrame())
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
