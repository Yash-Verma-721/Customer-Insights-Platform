import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, build_inventory_profile, money
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=t, b=b))
    return fig

def show_inventory_analytics():
    render_header("Inventory Analytics", "Track stock health, velocity, and forecasting requirements.", "Inventory Analytics")

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
    
    # 1. Executive KPIs
    st.markdown("### Executive KPIs")
    if not has_stock:
        st.info("Awaiting stock/inventory fields in the active dataset.")
        
    total_stock = profile["stock"].sum() if not profile.empty and "stock" in profile.columns else 0
    avg_stock = profile["stock"].mean() if not profile.empty and "stock" in profile.columns else 0
    
    turnover = "N/A"
    if not profile.empty and "orders" in profile.columns and total_stock > 0:
        total_orders = profile["orders"].sum()
        if total_orders > 0:
            turnover = f"{total_orders / total_stock:.2f}x"
            
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Stock", f"{int(total_stock):,}")
    k2.metric("Inventory Value", money(metrics.get("inventory_value", 0)))
    k3.metric("Low Stock Items", f"{metrics.get('low_stock_count', 0):,}")
    k4.metric("Avg Stock", f"{int(avg_stock):,}")
    k5.metric("Turnover Ratio", turnover)
    
    # 2. Charts
    st.markdown("### Inventory Health")
    if has_stock and not profile.empty:
        c1, c2 = st.columns(2)
        with c1:
            if "category" in profile.columns and not profile["category"].isna().all():
                cat_stock = profile.groupby("category", as_index=False)["stock"].sum().sort_values("stock", ascending=False).head(10)
                fig_cat = px.bar(cat_stock, x="category", y="stock", title="Stock Volume by Category", text_auto=".2s")
                st.plotly_chart(_apply_chart_layout(fig_cat, height=350), use_container_width=True)
            else:
                st.info("No category data available for stock distribution.")
                
            if "inventory_value" in profile.columns:
                top_val = profile.sort_values("inventory_value", ascending=False).head(10)
                fig_val = px.bar(top_val, x="product", y="inventory_value", title="Top Inventory Value Items", text_auto=".2s")
                st.plotly_chart(_apply_chart_layout(fig_val, height=350), use_container_width=True)
                
        with c2:
            low_stock_df = profile[(profile["stock"] > 0) & (profile["stock"] < 10)].sort_values("stock")
            if not low_stock_df.empty:
                fig_low = px.bar(low_stock_df.head(10), x="product", y="stock", title="Low Stock Products (<10 units)")
                st.plotly_chart(_apply_chart_layout(fig_low, height=350), use_container_width=True)
            else:
                st.success("No low stock products detected.")
                
            fig_dist = px.histogram(profile, x="stock", title="Stock Distribution", nbins=20)
            st.plotly_chart(_apply_chart_layout(fig_dist, height=350), use_container_width=True)
    else:
        st.info("Inventory charts will be populated when stock-level data is detected.")
    
    # 3. Insights
    st.markdown("### Insights")
    if has_stock and not profile.empty:
        overstock = profile.loc[profile["stock"].idxmax()]
        out_of_stock_count = metrics.get("out_of_stock_count", 0)
        
        st.info(f"**Overstock Alert:** {overstock['product']} currently has the highest stock volume ({int(overstock['stock'])} units). Consider whether holding this inventory is cost-effective.")
        
        if out_of_stock_count > 0:
            st.error(f"**Understock Alert:** There are {out_of_stock_count} products completely out of stock. Immediate replenishment may be necessary.")
        else:
            st.success("**Understock Check:** All tracked products currently have available stock.")
            
        low_stock_df = profile[(profile["stock"] > 0) & (profile["stock"] < 10)]
        if not low_stock_df.empty:
            reorder = ", ".join(low_stock_df["product"].astype(str).head(3).tolist())
            st.warning(f"**Reorder Suggestions:** The following items have critically low stock: {reorder}.")
    else:
        st.info("Inventory analytics help prevent stockouts on high-performing products and reduce holding costs on slow-moving items.")
    
    # 4. Detailed Tables
    with st.expander("Inventory Summary"):
        if has_stock and not profile.empty:
            st.dataframe(profile.sort_values("stock", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.write("Detailed data unavailable.")
            
    st.markdown("---")
    st.markdown("### 📄 Module Report")
    
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
