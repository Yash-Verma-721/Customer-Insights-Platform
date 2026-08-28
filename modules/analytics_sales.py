import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, build_sales_profile, money, percent
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

def show_sales_analytics():
    with page_wrapper():
        df, source_label, source_name = get_analytics_df("sales")

        # ---------------- Tier 1: Executive Header ---------------- #
        page_header(
            title="Sales Analytics",
            subtitle=f"Active Dataset: {source_name or 'Sales Overview'} | Access Level: Executive",
            status="Nominal",
            status_type="success"
        )
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

        # ---------------- Tier 2: Quick KPI Grid ---------------- #
        k1, k2, k3, k4 = st.columns(4)

        growth = metrics.get("growth_pct", 0)
        growth_trend = "up" if growth >= 0 else "down"

        with k1:
            render_kpi_card(
                "Total Revenue",
                money(metrics.get("total_sales", 0)),
                f"{abs(growth):.1f}% vs last period" if "growth_pct" in metrics else None,
                growth_trend,
                ICON_SALES
            )

        with k2:
            render_kpi_card(
                "Total Orders Processed",
                f"{metrics.get('total_orders', 0):,}",
                "Order Volume",
                "up",
                ICON_REPORT
            )

        with k3:
            render_kpi_card(
                "Avg Order Value",
                money(metrics.get("avg_order_value", 0)),
                "Purchase Size",
                "up",
                ICON_SALES
            )

        with k4:
            render_kpi_card(
                "Avg Daily Revenue",
                money(avg_daily_sales),
                "Daily Run-Rate",
                "up",
                ICON_TREND_UP
            )

        # ---------------- Tier 3: Primary Analytics Grid (Responsive 2:1 Bento Layout) ---------------- #
        if has_dates and not monthly_summary.empty:
            bento_left, bento_right = st.columns([2, 1])

            with bento_left:
                with chart_container("Revenue Performance Trend", subtitle="Monthly revenue timeline and performance trajectory"):
                    fig_rev = px.line(monthly_summary, x="Month", y="Revenue", markers=True, title="Revenue Trend")
                    st.plotly_chart(_apply_chart_layout(fig_rev, height=320), use_container_width=True)

            with bento_right:
                with bento_card("Sales Summary", ICON_AI):
                    render_metric_tile("Growth Rate", percent(metrics.get("growth_pct", 0)), metrics.get("growth_pct", 0))
                    render_metric_tile("Avg Daily Revenue", money(avg_daily_sales))
                    render_metric_tile("Total Orders", f"{metrics.get('total_orders', 0):,}")
                    render_metric_tile("Avg Order Value", money(metrics.get("avg_order_value", 0)))

                if best_month is not None and worst_month is not None:
                    with bento_card("Performance Leaders", ICON_TREND_UP):
                        render_ranking_list([
                            {"name": f"{best_month['Month']}", "value": f"🥇 Best ({money(best_month['Revenue'])})"},
                            {"name": f"{worst_month['Month']}", "value": f"🥈 Lowest ({money(worst_month['Revenue'])})"}
                        ])

            # ---------------- Tier 4: Secondary Analytics Grid (50% / 50%) ---------------- #
            sec1, sec2 = st.columns(2)

            with sec1:
                with chart_container("Order Volume & Trends", subtitle="Monthly order count progression"):
                    fig_ord = px.line(monthly_summary, x="Month", y="Orders", markers=True, title="Order Trend")
                    st.plotly_chart(_apply_chart_layout(fig_ord, height=320), use_container_width=True)

            with sec2:
                with chart_container("Monthly Revenue Distribution", subtitle="Period volume comparison"):
                    fig_bar = px.bar(monthly_summary, x="Month", y="Revenue", text_auto=".2s", title="Monthly Sales Volume")
                    st.plotly_chart(_apply_chart_layout(fig_bar, height=320), use_container_width=True)

        else:
            with chart_container("Sales Distribution Analysis"):
                st.info("Date column was not detected, so timeline analysis is unavailable.")
                if columns.get("revenue"):
                    st.plotly_chart(_apply_chart_layout(px.histogram(profile, x="revenue", nbins=30, title="Order Value Distribution"), height=380), use_container_width=True)
                else:
                    st.warning("Revenue column was not detected. Add a sales, amount, revenue, or order value field for value analysis.")

        # ---------------- Tier 5: Bottom Intelligence & ML Recommendations ---------------- #
        section_header("Sales Intelligence & AI Recommendations", subtitle="Performance analysis, anomaly alerts, and ML sales forecast")

        bot1, bot2 = st.columns(2)

        with bot1:
            with chart_container("Sales Alerts & Growth Summary"):
                if has_dates and not monthly_summary.empty:
                    if best_month is not None:
                        render_info_card("Peak Performance Period", f"Best month: {best_month['Month']} with {money(best_month['Revenue'])} revenue across {best_month['Orders']} orders.", ICON_TREND_UP, "success")
                    if worst_month is not None:
                        render_info_card("Lowest Volume Period", f"Lowest month: {worst_month['Month']} with {money(worst_month['Revenue'])} revenue across {worst_month['Orders']} orders.", ICON_ALERT, "warning")

                    growth_val = metrics.get("growth_pct", 0)
                    if growth_val > 0:
                        render_info_card("Growth Trajectory", f"Positive growth trend of {percent(growth_val)} vs previous period.", ICON_SUCCESS, "success")
                    elif growth_val < 0:
                        render_info_card("Growth Warning", f"Decline of {percent(growth_val)} vs previous period. Strategic intervention recommended.", ICON_ALERT, "danger")
                    else:
                        render_info_card("Growth Status", "Revenue growth remained flat in the recent period.", ICON_INFO, "info")
                else:
                    render_info_card("Distribution Insight", "Monthly revenue trend indicates macro seasonality while monetary distribution reveals transaction clustering.", ICON_INFO, "info")

        with bot2:
            with chart_container("AI Sales Forecast & Strategic Advice"):
                if has_dates and not monthly_summary.empty:
                    from utils.ml_models import ml_sales_forecast
                    forecast = ml_sales_forecast(monthly_summary)

                    if forecast.get("status") == "success":
                        render_metric_tile("Predicted Next Period Revenue", money(forecast["forecast_revenue"]))
                        render_metric_tile("Projected Trend Indicator", forecast["trend"])
                        render_metric_tile("Model Confidence Level", forecast["confidence"])
                        render_info_card("AI Sales Forecast Recommendation", forecast['recommendation'], ICON_AI, "info")
                    else:
                        render_info_card("Forecast Status", "ML forecast model pending additional timeframe data.", ICON_AI, "info")
                else:
                    render_info_card("AI Forecast Status", "Connect a time-series dataset to enable machine learning sales forecasting.", ICON_AI, "info")

        # ---------------- Executive Insight Strip (NEW) ---------------- #
        with chart_container("Executive Insight Summary"):
            insight_bullets = []
            
            # Growth Trajectory Bullet
            growth_val = metrics.get("growth_pct", 0)
            if growth_val > 0:
                insight_bullets.append(f"• **Revenue Growth:** Increased by {percent(growth_val)} compared to previous period.")
            elif growth_val < 0:
                insight_bullets.append(f"• **Revenue Growth:** Decreased by {percent(abs(growth_val))} compared to previous period.")
            else:
                insight_bullets.append("• **Revenue Growth:** Remained flat in the recent reporting period.")
                
            # Peak Performance Bullet
            if best_month is not None:
                insight_bullets.append(f"• **Peak Volume Period:** {best_month['Month']} generated highest revenue ({money(best_month['Revenue'])}) across {best_month['Orders']} orders.")
                
            # Forecast & Recommendation Bullet
            if forecast and forecast.get("status") == "success":
                insight_bullets.append(f"• **Forecast Direction:** Projected {forecast['trend'].lower()} trajectory for next period ({forecast['confidence']} confidence).")
                insight_bullets.append(f"• **Strategic Action:** {forecast['recommendation']}")

            insight_msg = "\n\n".join(insight_bullets)
            render_info_card("Executive Summary", insight_msg, ICON_AI, "info")

        # ---------------- Detailed Data & Report Generator ---------------- #
        with chart_container("Detailed Sales Data & Report Generator"):
            with st.expander("Detailed Sales Data Tables"):
                if has_dates and not monthly_summary.empty:
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        st.markdown("**Monthly Summary**")
                        st.dataframe(monthly_summary, use_container_width=True, hide_index=True)
                    with tc2:
                        st.markdown("**Top Periods**")
                        st.dataframe(monthly_summary.sort_values("Revenue", ascending=False).head(10), use_container_width=True, hide_index=True)
                else:
                    st.dataframe(profile.head(100), use_container_width=True)

            st.markdown("---")
            st.markdown("**📄 Generate Sales Analytics Report**")
            if st.button("Generate Sales Report", type="primary"):
                with branded_spinner("Generating Sales Report..."):
                    from modules.reports.sales_report import build_sales_report_blocks
                    from modules.reports.report_utils import generate_excel_bytes

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
