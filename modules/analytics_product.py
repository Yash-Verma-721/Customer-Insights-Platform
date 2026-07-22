import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, build_inventory_profile, money
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=t, b=b))
    return fig

def show_product_analytics():
    render_header("Product Analytics", "Identify top-selling products, categories, and inventory velocity.", "Product Analytics")
    
    if "df" not in st.session_state or st.session_state.df is None or st.session_state.df.empty:
        render_empty_state()
        render_footer("Product Analytics")
        return

    df = st.session_state.df
    with branded_spinner("Loading product analytics..."):
        from utils.cache import get_cached_metric
        detected = get_cached_metric("detected_mp", detect_marketplace_columns, df)
        profile, metrics, columns = get_cached_metric("inv_profile", build_inventory_profile, df, detected)

    has_product = metrics.get("has_product_column", False)
    
    # 1. Executive KPIs
    st.markdown("### Executive KPIs")
    if not has_product:
        st.info("Awaiting product identification fields in the active dataset.")
        
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Products", f"{metrics.get('total_products', 0):,}")
    k2.metric("Categories", f"{metrics.get('total_categories', 0):,}")
    k3.metric("Avg Price", money(metrics.get("avg_price", 0)))
    k4.metric("Avg Rating", f"{metrics.get('avg_rating', 0):.2f}" if metrics.get("avg_rating", 0) > 0 else "N/A")
    k5.metric("Stock Value", money(metrics.get("inventory_value", 0)))
    
    # 2. Charts
    st.markdown("### Product Performance")
    if has_product and not profile.empty:
        c1, c2 = st.columns(2)
        with c1:
            top_products = profile.sort_values("orders", ascending=False).head(10)
            fig_top = px.bar(top_products, x="product", y="orders", title="Top Products by Orders", text_auto=".2s")
            st.plotly_chart(_apply_chart_layout(fig_top, height=350), use_container_width=True)
            
            if "category" in profile.columns and not profile["category"].isna().all():
                cat_df = profile["category"].value_counts().reset_index()
                cat_df.columns = ["category", "count"]
                fig_cat = px.pie(cat_df.head(10), names="category", values="count", title="Category Distribution (Top 10)")
                st.plotly_chart(_apply_chart_layout(fig_cat, height=350), use_container_width=True)
            else:
                st.info("No category data available for distribution chart.")
                
        with c2:
            if not profile["avg_price"].isna().all():
                fig_price = px.histogram(profile, x="avg_price", title="Price Distribution", nbins=20)
                st.plotly_chart(_apply_chart_layout(fig_price, height=350), use_container_width=True)
            else:
                st.info("No pricing data available for price distribution chart.")
                
            if not profile["avg_rating"].isna().all():
                fig_rate = px.histogram(profile, x="avg_rating", title="Rating Distribution", nbins=20)
                st.plotly_chart(_apply_chart_layout(fig_rate, height=350), use_container_width=True)
            else:
                st.info("No rating data available for rating distribution chart.")
    else:
        st.info("Product performance charts will be populated when product or SKU data is detected.")
    
    # 3. Insights
    st.markdown("### Insights")
    if has_product and not profile.empty:
        best_product = profile.loc[profile["orders"].idxmax()]
        lowest_product = profile.loc[profile["orders"].idxmin()]
        
        st.success(f"**Best Product:** {best_product['product']} generated the most orders ({int(best_product['orders'])}).")
        st.warning(f"**Lowest Product:** {lowest_product['product']} generated the lowest orders ({int(lowest_product['orders'])}).")
        
        if "category" in profile.columns and profile["category"].nunique() > 0:
            top_3_cats = profile["category"].value_counts().head(3)
            leaders = ", ".join(top_3_cats.index.astype(str).tolist())
            st.info(f"**Top Categories:** The most prominent product categories are {leaders}.")
    else:
        st.info("Product analytics help prevent stockouts on high-performing items and reduce holding costs on slow-moving inventory.")
    
    # 4. Detailed Tables
    with st.expander("Product Summary"):
        if has_product and not profile.empty:
            st.dataframe(profile.sort_values("orders", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.write("Detailed data unavailable.")
            
    st.markdown("---")
    st.markdown("### 📄 Module Report")
    
    if st.button("Generate Product Report", type="primary"):
        with branded_spinner("Generating Product Report..."):
            from modules.reports.product_report import build_product_report_blocks
            from modules.reports.report_utils import generate_excel_bytes
            
            report_metrics = metrics.copy()
            top_df = pd.DataFrame()
            if has_product and not profile.empty:
                top_df = profile.sort_values("orders", ascending=False).head(10)
                report_metrics["best_product"] = profile.loc[profile["orders"].idxmax()]['product'] if not profile.empty else "N/A"
                report_metrics["best_product_revenue"] = profile["revenue"].max() if "revenue" in profile.columns and not profile.empty else 0
                report_metrics["lowest_product_revenue"] = profile["revenue"].min() if "revenue" in profile.columns and not profile.empty else 0
                
            blocks = build_product_report_blocks(report_metrics, top_df)
            st.session_state["product_report_bytes"] = generate_excel_bytes(blocks, "Product Report")
            
    if "product_report_bytes" in st.session_state:
        st.download_button(
            label="Download Product Report",
            data=st.session_state["product_report_bytes"],
            file_name="product_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary"
        )
        
    render_footer("Product Analytics")
