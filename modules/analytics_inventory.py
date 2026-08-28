import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, build_inventory_profile, money
from utils.ui_helpers import render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner

from utils.ui_components import (
    page_wrapper, render_page_header, render_section_header,
    render_kpi_card, render_info_card, render_table_toolbar
)
from utils.ui_constants import *

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(
        height=height, 
        margin=dict(l=20, r=20, t=t, b=b),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="'Hanken Grotesk', sans-serif",
        font_color="#e1e2ea"
    )
    return fig

def show_inventory_analytics():
    with page_wrapper():
        render_page_header(
            "Inventory Analytics", 
            "Track stock health, velocity, and forecasting requirements."
        )

        df, source_label, source_name = get_analytics_df("inventory")
        render_data_source_banner(source_label, source_name)

        if df is None or df.empty:
            render_empty_state()
            render_footer("Inventory Analytics")
            return
            
        with branded_spinner("Loading inventory analytics..."):
            from utils.cache import get_cached_metric
            detected = get_cached_metric("detected_inv", detect_marketplace_columns, df)
            profile, metrics, columns = get_cached_metric("inv_profile", build_inventory_profile, df, detected)

        has_stock = metrics.get("has_stock_column", False)
        
        # 1. Inventory Lifecycle Overview & Executive KPIs
        render_section_header("Inventory Lifecycle Overview")
        if not has_stock:
            render_info_card("Awaiting Data", "Awaiting stock/inventory fields in the active dataset.", ICON_INFO, "info")
            
        total_stock = profile["stock"].sum() if not profile.empty and "stock" in profile.columns else 0
        avg_stock = profile["stock"].mean() if not profile.empty and "stock" in profile.columns else 0
        
        total_reserved = df["reserved_quantity"].sum() if "reserved_quantity" in df.columns else 0
        out_of_stock_items = len(df[df["current_stock"] <= 0]) if "current_stock" in df.columns else 0
        
        turnover = "0x"
        if not profile.empty and "orders" in profile.columns and total_stock > 0:
            total_orders = profile["orders"].sum()
            if total_orders > 0:
                turnover = f"{total_orders / total_stock:.2f}x"
                
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card("Total Products", f"{len(df):,}", "-", "neutral", ICON_PRODUCT)
        with c2:
            render_kpi_card("Total Available", f"{int(total_stock):,}", "-", "neutral", ICON_PRODUCT)
        with c3:
            render_kpi_card("Total Reserved", f"{int(total_reserved):,}", "-", "neutral", ICON_PRODUCT)
        with c4:
            oos_trend = "up" if out_of_stock_items == 0 else "down"
            render_kpi_card("Out of Stock", f"{out_of_stock_items:,}", "-", oos_trend, ICON_ALERT)

        st.markdown("<br>", unsafe_allow_html=True)
        render_section_header("Executive KPIs")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_kpi_card("Inventory Value", money(metrics.get("inventory_value", 0)), "-", "neutral", ICON_SALES)
        with k2:
            render_kpi_card("Low Stock Items", f"{metrics.get('low_stock_count', 0):,}", "-", "down" if metrics.get('low_stock_count', 0) > 0 else "up", ICON_ALERT)
        with k3:
            render_kpi_card("Avg Stock", f"{int(avg_stock):,}", "-", "neutral", ICON_PRODUCT)
        with k4:
            render_kpi_card("Turnover Ratio", turnover, "-", "neutral", ICON_REPORT)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. Charts
        render_section_header("Inventory Health")
        if has_stock and not profile.empty:
            c1, c2 = st.columns(2)
            with c1:
                if "category" in profile.columns and not profile["category"].isna().all():
                    cat_stock = profile.groupby("category", as_index=False)["stock"].sum().sort_values("stock", ascending=False).head(10)
                    fig_cat = px.bar(cat_stock, x="category", y="stock", title="Stock Volume by Category", text_auto=".2s")
                    fig_cat.update_traces(marker_color='#a8c8ff')
                    st.plotly_chart(_apply_chart_layout(fig_cat, height=350), use_container_width=True)
                else:
                    st.info("No category data available for stock distribution.")
                    
                if "inventory_value" in profile.columns:
                    top_val = profile.sort_values("inventory_value", ascending=False).head(10)
                    fig_val = px.bar(top_val, x="product", y="inventory_value", title="Top Inventory Value Items", text_auto=".2s")
                    fig_val.update_traces(marker_color='#a8c8ff')
                    st.plotly_chart(_apply_chart_layout(fig_val, height=350), use_container_width=True)
                    
            with c2:
                low_stock_df = profile[(profile["stock"] > 0) & (profile["stock"] < 10)].sort_values("stock")
                if not low_stock_df.empty:
                    fig_low = px.bar(low_stock_df.head(10), x="product", y="stock", title="Low Stock Products (<10 units)")
                    fig_low.update_traces(marker_color='#ffb4ab')
                    st.plotly_chart(_apply_chart_layout(fig_low, height=350), use_container_width=True)
                else:
                    st.success("No low stock products detected.")
                    
                fig_dist = px.histogram(profile, x="stock", title="Stock Distribution", nbins=20)
                fig_dist.update_traces(marker_color='#b7c8e1')
                st.plotly_chart(_apply_chart_layout(fig_dist, height=350), use_container_width=True)
        else:
            st.info("Inventory charts will be populated when stock-level data is detected.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 3. Insights
        render_section_header("Insights")
        if has_stock and not profile.empty:
            overstock = profile.loc[profile["stock"].idxmax()]
            out_of_stock_count = metrics.get("out_of_stock_count", 0)
            
            render_info_card(
                "Overstock Alert", 
                f"{overstock['product']} currently has the highest stock volume ({int(overstock['stock'])} units). Consider whether holding this inventory is cost-effective.", 
                ICON_INFO, "info"
            )
            
            if out_of_stock_count > 0:
                render_info_card("Understock Alert", f"There are {out_of_stock_count} products completely out of stock. Immediate replenishment may be necessary.", ICON_ALERT, "danger")
            else:
                render_info_card("Understock Check", "All tracked products currently have available stock.", ICON_SUCCESS, "success")
                
            low_stock_df = profile[(profile["stock"] > 0) & (profile["stock"] < 10)]
            if not low_stock_df.empty:
                reorder = ", ".join(low_stock_df["product"].astype(str).head(3).tolist())
                render_info_card("Reorder Suggestions", f"The following items have critically low stock: {reorder}.", ICON_ALERT, "warning")
        else:
            st.info("Inventory analytics help prevent stockouts on high-performing products and reduce holding costs on slow-moving items.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 4. Detailed Tables
        render_table_toolbar("Inventory Summary", "Download CSV")
        if has_stock and not profile.empty:
            st.dataframe(profile.sort_values("stock", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.write("Detailed data unavailable.")
                
        st.markdown("---")
        render_section_header("Module Report")
        
        if st.button("Generate Inventory Report", type="primary"):
            with branded_spinner("Generating Inventory Report..."):
                from modules.reports.inventory_report import build_inventory_report_blocks
                from modules.reports.report_utils import generate_excel_bytes
                
                report_metrics = metrics.copy()
                report_metrics["total_stock"] = total_stock
                
                stock_df = pd.DataFrame()
                if has_stock and not profile.empty:
                    stock_df = profile[(profile["stock"] > 0) & (profile["stock"] < 10)].sort_values("stock")
                    
                blocks = build_inventory_report_blocks(report_metrics, stock_df)
                st.session_state["inventory_report_bytes"] = generate_excel_bytes(blocks, "Inventory Report")
                
        if "inventory_report_bytes" in st.session_state:
            st.download_button(
                label="Download Inventory Report",
                data=st.session_state["inventory_report_bytes"],
                file_name="inventory_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="secondary"
            )
            
        render_footer("Inventory Analytics")
