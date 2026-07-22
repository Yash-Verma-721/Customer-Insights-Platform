import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, build_vendor_profile, money, percent
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=t, b=b))
    return fig

def show_vendor_analytics():
    render_header("Vendor Analytics", "Monitor vendor performance, fulfillment metrics, and profitability.", "Vendor Analytics")

    df, source_label, source_name = get_analytics_df("vendor")
    render_data_source_banner(source_label, source_name)

    if df is None or df.empty:
        render_empty_state()
        render_footer("Vendor Analytics")
        return
    with branded_spinner("Loading vendor analytics..."):
        from utils.cache import get_cached_metric
        detected = get_cached_metric("detected_vendor", detect_marketplace_columns, df)
        profile, metrics, columns = get_cached_metric("vendor_profile", build_vendor_profile, df, detected)

    has_vendor = metrics.get("has_vendor_column", False)
    
    # 1. Executive KPIs
    st.markdown("### Executive KPIs")
    if not has_vendor:
        st.info("Awaiting vendor identification fields in the active dataset.")
        
    avg_rating = profile["avg_rating"].mean() if not profile["avg_rating"].isna().all() else 0.0
    avg_fulfillment = profile["fulfillment_pct"].mean() if not profile["fulfillment_pct"].isna().all() else 0.0
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Vendors", f"{metrics.get('total_vendors', 0):,}")
    k2.metric("Revenue", money(metrics.get("total_revenue", 0)))
    k3.metric("Orders", f"{metrics.get('total_orders', 0):,}")
    k4.metric("Avg Rating", f"{avg_rating:.2f}" if avg_rating > 0 else "N/A")
    k5.metric("Fulfillment %", percent(avg_fulfillment) if avg_fulfillment > 0 else "N/A")
    
    # 2. Charts
    st.markdown("### Vendor Performance")
    if has_vendor and not profile.empty:
        c1, c2 = st.columns(2)
        with c1:
            top_vendors = profile.sort_values("revenue", ascending=False).head(10)
            fig_top = px.bar(top_vendors, x="vendor", y="revenue", title="Top Vendors by Revenue", text_auto=".2s")
            st.plotly_chart(_apply_chart_layout(fig_top, height=350), use_container_width=True)
            
            # Pie Chart
            top_5 = profile.sort_values("revenue", ascending=False).head(5)
            others_revenue = profile.sort_values("revenue", ascending=False).iloc[5:]["revenue"].sum()
            if others_revenue > 0:
                others_df = pd.DataFrame({"vendor": ["Others"], "revenue": [others_revenue]})
                pie_df = pd.concat([top_5[["vendor", "revenue"]], others_df])
            else:
                pie_df = top_5[["vendor", "revenue"]]
                
            fig_pie = px.pie(pie_df, names="vendor", values="revenue", title="Revenue Share by Vendor")
            st.plotly_chart(_apply_chart_layout(fig_pie, height=350), use_container_width=True)
            
        with c2:
            if not profile["avg_rating"].isna().all():
                fig_rate = px.histogram(profile, x="avg_rating", title="Vendor Rating Distribution", nbins=20)
                st.plotly_chart(_apply_chart_layout(fig_rate, height=350), use_container_width=True)
            else:
                st.info("No rating data available for rating distribution chart.")
                
            if not profile["fulfillment_pct"].isna().all():
                fig_fulfill = px.histogram(profile, x="fulfillment_pct", title="Fulfillment % Distribution", nbins=20)
                st.plotly_chart(_apply_chart_layout(fig_fulfill, height=350), use_container_width=True)
            else:
                st.info("No status data available for fulfillment % chart.")
    else:
        st.info("Vendor performance charts will be populated when vendor or supplier data is detected.")
    
    # 3. Insights
    st.markdown("### Insights")
    if has_vendor and not profile.empty:
        best_vendor = profile.loc[profile["revenue"].idxmax()]
        lowest_vendor = profile.loc[profile["revenue"].idxmin()]
        
        st.success(f"**Best Vendor:** {best_vendor['vendor']} is driving the most revenue ({money(best_vendor['revenue'])}).")
        st.warning(f"**Lowest Vendor:** {lowest_vendor['vendor']} generated the lowest revenue ({money(lowest_vendor['revenue'])}).")
        
        top_3 = profile.sort_values("revenue", ascending=False).head(3)
        leaders = ", ".join(top_3["vendor"].astype(str).tolist())
        st.info(f"**Revenue Leaders:** The top performing vendors are {leaders}.")
    else:
        st.info("Vendor analytics provide visibility into the supply chain and help isolate underperforming suppliers.")
    
    # 4. Detailed Tables
    with st.expander("Vendor Summary"):
        if has_vendor and not profile.empty:
            display_df = profile.sort_values("revenue", ascending=False).drop(columns=["revenue_rank", "order_rank"], errors="ignore")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.write("Detailed data unavailable.")
            
    st.markdown("---")
    st.markdown("### 📄 Module Report")
    
    if st.button("Generate Vendor Report", type="primary"):
        with branded_spinner("Generating Vendor Report..."):
            from modules.reports.vendor_report import build_vendor_report_blocks
            from modules.reports.report_utils import generate_excel_bytes
            
            report_metrics = metrics.copy()
            report_metrics["avg_rating"] = avg_rating
            
            top_df = pd.DataFrame()
            if has_vendor and not profile.empty:
                top_df = profile.sort_values("revenue", ascending=False).head(10)
                report_metrics["top_vendor_by_revenue"] = profile.loc[profile["revenue"].idxmax()]['vendor'] if not profile.empty else "N/A"
                report_metrics["top_vendor_revenue"] = profile["revenue"].max() if not profile.empty else 0
                report_metrics["lowest_vendor_revenue"] = profile["revenue"].min() if not profile.empty else 0
                
            blocks = build_vendor_report_blocks(report_metrics, top_df)
            st.session_state["vendor_report_bytes"] = generate_excel_bytes(blocks, "Vendor Report")
            
    if "vendor_report_bytes" in st.session_state:
        st.download_button(
            label="Download Vendor Report",
            data=st.session_state["vendor_report_bytes"],
            file_name="vendor_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary"
        )
        
    render_footer("Vendor Analytics")
