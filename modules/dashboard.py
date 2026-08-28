import streamlit as st
import pandas as pd
import plotly.express as px

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

from utils.ui_components import (
    page_wrapper, page_header, section_header,
    kpi_card, info_card, render_metric_tile,
    bento_card, ranking_card, chart_container,
    render_page_header, render_section_header,
    render_kpi_card, render_info_card, render_ranking_list
)
from utils.ui_constants import *

def show_dashboard():
    with page_wrapper():
        role = st.session_state.get('role', 'Manager')
        user_name = st.session_state.get('full_name', 'Analyst')
        role_display = 'Analyst' if role == 'Business Analyst' else role

        from utils.data_source_helper import get_analytics_df, render_data_source_banner
        df, source_label, source_name = get_analytics_df("marketplace")

        # ---------------- 1. EXECUTIVE HEADER ---------------- #
        page_header(
            title="Executive Dashboard",
            subtitle=f"Active Dataset: {source_name or 'Default Marketplace'} | Access Level: {role_display}",
            status="System Nominal",
            status_type="success"
        )

        # Source Banner
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

        # ---------------- 2. QUICK KPI GRID ---------------- #
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

        with kpi_col1:
            growth = sales_metrics.get("growth_pct", 0)
            trend_dir = 'up' if growth >= 0 else 'down'
            render_kpi_card(
                "Gross Revenue",
                money(sales_metrics.get("total_sales", 0)),
                f"{abs(growth):.1f}% vs last period" if "growth_pct" in sales_metrics else None,
                trend_dir,
                ICON_SALES
            )

        with kpi_col2:
            render_kpi_card(
                "Marketplace Commission",
                money(total_commission),
                "Operating Margin",
                "up",
                ICON_REPORT
            )

        with kpi_col3:
            render_kpi_card(
                "Active Customers",
                f"{cust_metrics.get('total_customers', 0):,}",
                "Customer Base",
                "up",
                ICON_CUSTOMER
            )

        with kpi_col4:
            render_kpi_card(
                "Vendor Approval Rate",
                f"{approval_rate:.1f}%",
                "Vendor Health",
                "up",
                ICON_VENDOR
            )

        # ---------------- 3. PRIMARY ANALYTICS BENTO GRID (RESPONSIVE 2:1 LAYOUT) ---------------- #
        bento_left, bento_right = st.columns([2, 1])

        with bento_left:
            # Main Revenue Performance Chart Container
            with chart_container("Revenue Performance", subtitle="Monthly revenue trend and volume summary"):
                if "order_date" in df.columns and "total_amount" in df.columns:
                    try:
                        df['order_date'] = pd.to_datetime(df['order_date'])
                        monthly = df.groupby(df['order_date'].dt.to_period('M'))['total_amount'].sum().reset_index()
                        monthly['order_date'] = monthly['order_date'].astype(str)
                        fig = px.area(monthly, x='order_date', y='total_amount', markers=True)
                        fig.update_traces(line_color='#a8c8ff', fillcolor='rgba(168, 200, 255, 0.2)')
                        fig.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_family="'Hanken Grotesk', sans-serif",
                            font_color="#e1e2ea",
                            margin=dict(l=10, r=10, t=10, b=10),
                            height=280
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        st.info("Chart data not available")
                else:
                    st.info("Chart data not available")

            # Sub-Card Row: Customer & Sales + Inventory Health
            sub_col1, sub_col2 = st.columns(2)

            with sub_col1:
                with chart_container("Customer & Sales Intelligence"):
                    render_metric_tile("Total Customers", f"{cust_metrics.get('total_customers', 0):,}")
                    render_metric_tile("Total Orders Processed", f"{total_orders:,}")
                    render_metric_tile("Avg Customer Revenue", money(cust_metrics.get('avg_customer_value', 0)))

            with sub_col2:
                with chart_container("Inventory & Supply Chain Health"):
                    render_metric_tile("Total Inventory Items", f"{inv_metrics.get('total_items', 0):,}")
                    render_metric_tile("Low Stock Alert Items", f"{inv_metrics.get('low_stock_count', 0)}")
                    render_metric_tile("Pending Vendor Settlements", f"{pending_settlements}")

        with bento_right:
            # Executive Summary Card (~55% height)
            with bento_card("Executive Summary", ICON_AI):
                render_metric_tile("Avg Order Value", money(sales_metrics.get('avg_order_value', 0)))
                render_metric_tile("Customer Retention", percent(cust_metrics.get('repeat_rate', 0)), cust_metrics.get('repeat_rate', 0))
                render_metric_tile("Active Vendors", vendor_metrics.get('total_vendors', 0))
                render_metric_tile("Total Inventory Value", money(inv_metrics.get('inventory_value', 0)))
                render_metric_tile("Payment Success Rate", percent(payment_metrics.get('success_rate', 0)), payment_metrics.get('success_rate', 0))

            # Top Performers Card (~45% height)
            with bento_card("Top Performers", ICON_TREND_UP):
                top_vendor = vendor_metrics.get("top_vendor_by_revenue", "N/A")
                top_products_dict = inv_metrics.get("top_products", {})
                top_product = list(top_products_dict.keys())[0] if top_products_dict else "N/A"
                top_cats_dict = inv_metrics.get("top_categories", {})
                best_category = list(top_cats_dict.keys())[0] if top_cats_dict else "N/A"

                render_ranking_list([
                    {"name": top_vendor, "value": "🥇 Top Vendor"},
                    {"name": top_product, "value": "🥈 Top Product"},
                    {"name": best_category, "value": "🥉 Top Category"}
                ])

        # ---------------- 4. BOTTOM INTELLIGENCE AREA ---------------- #
        section_header("Bottom Intelligence & AI Insights", subtitle="Prioritized system alerts and strategic AI recommendations")

        bot_col1, bot_col2 = st.columns(2)

        with bot_col1:
            with chart_container("System Alerts & Operational Feed"):
                alerts_shown = 0
                max_alerts = 2

                if inv_metrics.get("low_stock_count", 0) > 0 and alerts_shown < max_alerts:
                    render_info_card("Low Stock Warning", f"{inv_metrics['low_stock_count']} items are running low on inventory.", ICON_PRODUCT, "warning")
                    alerts_shown += 1

                if has_status and alerts_shown < max_alerts:
                    total = sum(order_status_counts.values())
                    if total > 0:
                        ret_rate = (order_status_counts.get("Returned", 0) / total) * 100
                        if ret_rate > 5.0:
                            render_info_card("High Returns Alert", f"Return rate is currently {ret_rate:.1f}%.", ICON_ALERT, "danger")
                            alerts_shown += 1

                if payment_metrics.get("failed_count", 0) > 0 and alerts_shown < max_alerts:
                    render_info_card("Failed Payment Risk", f"{payment_metrics['failed_count']} transactions failed processing.", ICON_SALES, "danger")
                    alerts_shown += 1

                if alerts_shown == 0:
                    render_info_card("System Nominal", "No critical alerts at this time. All systems nominal.", ICON_SUCCESS, "success")

        with bot_col2:
            with chart_container("Strategic Recommendations & AI Feed"):
                if not recs:
                    render_info_card("Recommendations", "No automated recommendations generated for the current dataset.", ICON_AI, "info")
                else:
                    top_recs = sorted(recs, key=lambda x: {"High": 0, "Medium": 1, "Low": 2}.get(x.get("priority", "Low"), 3))
                    for rec in top_recs[:2]:
                        priority = rec.get("priority", "Low")
                        msg = f"{rec.get('message', '')} (Action: {rec.get('action', '')})"
                        alert_type = "danger" if priority == "High" else "warning" if priority == "Medium" else "info"
                        render_info_card(rec.get('title', 'Insight'), msg, ICON_AI, alert_type)

        render_footer("Executive Dashboard")
