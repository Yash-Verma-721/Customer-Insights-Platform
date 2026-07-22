import streamlit as st
import pandas as pd
import plotly.express as px
from utils.customer_metrics import detect_marketplace_columns, money, percent
from utils.ui_helpers import render_header, render_empty_state, render_footer, branded_spinner
from utils.data_source_helper import get_analytics_df, render_data_source_banner

def _apply_chart_layout(fig, height=430, t=35, b=35):
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=t, b=b))
    return fig

def _process_payment_data(df, detected):
    payment_col = None
    for col in df.columns:
        lowered = str(col).lower()
        if any(kw in lowered for kw in ["payment", "method", "card", "gateway", "processor", "wallet"]):
            payment_col = col
            break
            
    revenue_col = detected.get("revenue", [None])[0] if detected.get("revenue") else None
    status_col = detected.get("status", [None])[0] if detected.get("status") else None
    
    total_revenue = 0.0
    avg_payment = 0.0
    if revenue_col:
        numeric_rev = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)
        total_revenue = float(numeric_rev.sum())
        if len(df) > 0:
            avg_payment = float(numeric_rev.mean())
            
    total_methods = df[payment_col].nunique() if payment_col else 0
    
    success_rate = 0.0
    failed_count = 0
    success_count = 0
    if status_col:
        s = df[status_col].astype(str).str.lower()
        success_mask = s.str.contains("success|complete|paid|approve", na=False)
        fail_mask = s.str.contains("fail|decline|reject|error|cancel", na=False)
        
        success_count = int(success_mask.sum())
        failed_count = int(fail_mask.sum())
        total_known = success_count + failed_count
        if total_known > 0:
            success_rate = (success_count / total_known) * 100
            
    payment_summary = pd.DataFrame()
    if payment_col:
        grouped = df.groupby(payment_col)
        payment_summary = pd.DataFrame(index=grouped.groups.keys())
        payment_summary["Transactions"] = grouped.size()
        
        if revenue_col:
            numeric_rev = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)
            payment_summary["Revenue"] = df.groupby(payment_col)[revenue_col].apply(lambda x: pd.to_numeric(x, errors="coerce").fillna(0).sum())
        else:
            payment_summary["Revenue"] = 0.0
            
        payment_summary = payment_summary.reset_index().rename(columns={"index": "Payment Method"})
        payment_summary = payment_summary.sort_values("Transactions", ascending=False)
        
    return {
        "total_revenue": total_revenue,
        "avg_payment": avg_payment,
        "total_methods": total_methods,
        "success_rate": success_rate,
        "failed_count": failed_count,
        "success_count": success_count,
        "payment_summary": payment_summary,
        "has_payment": payment_col is not None,
        "has_revenue": revenue_col is not None,
        "has_status": status_col is not None
    }

def show_payment_analytics():
    render_header("Payment Analytics", "Analyze transaction success rates, payment methods, and gateways.", "Payment Analytics")

    df, source_label, source_name = get_analytics_df("payment")
    render_data_source_banner(source_label, source_name)

    if df is None or df.empty:
        render_empty_state()
        render_footer("Payment Analytics")
        return
    with branded_spinner("Loading payment analytics..."):
        from utils.cache import get_cached_metric
        detected = get_cached_metric("detected_pay", detect_marketplace_columns, df)
        metrics = get_cached_metric("payment_profile", _process_payment_data, df, detected)

    has_payment = metrics.get("has_payment", False)
    has_status = metrics.get("has_status", False)
    summary = metrics.get("payment_summary", pd.DataFrame())
    
    # 1. Executive KPIs
    st.markdown("### Executive KPIs")
    if not has_payment:
        st.info("Awaiting payment method fields in the active dataset.")
        
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue", money(metrics.get("total_revenue", 0)))
    k2.metric("Payment Methods", f"{metrics.get('total_methods', 0)}")
    k3.metric("Avg Payment", money(metrics.get("avg_payment", 0)))
    k4.metric("Success Rate", percent(metrics.get("success_rate", 0)) if has_status else "N/A")
    k5.metric("Failed Payments", f"{metrics.get('failed_count', 0):,}" if has_status else "N/A")
    
    # 2. Charts
    st.markdown("### Transaction Analysis")
    c1, c2 = st.columns(2)
    with c1:
        if has_payment and not summary.empty:
            fig_meth = px.pie(summary, names="Payment Method", values="Transactions", title="Payment Method Distribution")
            st.plotly_chart(_apply_chart_layout(fig_meth, height=350), use_container_width=True)
        else:
            st.info("No payment method data available.")
            
        if has_status:
            status_df = pd.DataFrame({
                "Status": ["Success", "Failed"],
                "Count": [metrics.get("success_count", 0), metrics.get("failed_count", 0)]
            })
            if status_df["Count"].sum() > 0:
                fig_stat = px.bar(status_df, x="Status", y="Count", color="Status", title="Transaction Success vs Failure", text_auto=".2s")
                st.plotly_chart(_apply_chart_layout(fig_stat, height=350), use_container_width=True)
            else:
                st.info("Insufficient status counts for success vs failure chart.")
        else:
            st.info("No transactional status data available.")
            
    with c2:
        if has_payment and not summary.empty and metrics.get("has_revenue"):
            fig_rev = px.bar(summary.sort_values("Revenue", ascending=False), x="Payment Method", y="Revenue", title="Revenue by Payment Method", text_auto=".2s")
            st.plotly_chart(_apply_chart_layout(fig_rev, height=350), use_container_width=True)
        else:
            st.info("No cross-referenced payment and revenue data available.")
    
    # 3. Insights
    st.markdown("### Insights")
    if has_payment and not summary.empty:
        best_method = summary.loc[summary["Transactions"].idxmax()]
        st.success(f"**Preferred Payment:** '{best_method['Payment Method']}' is the most popular payment method with {best_method['Transactions']} transactions.")
        
        if metrics.get("has_revenue"):
            best_rev_method = summary.loc[summary["Revenue"].idxmax()]
            st.info(f"**Revenue Summary:** '{best_rev_method['Payment Method']}' drives the highest monetary volume ({money(best_rev_method['Revenue'])}).")
    else:
        st.info("Payment analytics help isolate gateway issues and preferred regional payment types.")
        
    if has_status:
        failed = metrics.get('failed_count', 0)
        rate = metrics.get('success_rate', 0)
        if failed > 0:
            st.warning(f"**Failed Payment Analysis:** There are {failed} failed transactions. A success rate of {rate:.1f}% indicates potential friction at checkout.")
        elif rate > 0:
            st.success("**Failed Payment Analysis:** All detected transactions processed successfully.")
    
    # 4. Detailed Tables
    with st.expander("Payment Summary"):
        if has_payment and not summary.empty:
            st.dataframe(summary.sort_values("Transactions", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.write("Detailed data unavailable.")
            
    st.markdown("---")
    st.markdown("### 📄 Module Report")
    
    if st.button("Generate Payment Report", type="primary"):
        with branded_spinner("Generating Payment Report..."):
            from modules.reports.payment_report import build_payment_report_blocks
            from modules.reports.report_utils import generate_excel_bytes
            
            blocks = build_payment_report_blocks(metrics, summary if has_payment else pd.DataFrame())
            st.session_state["payment_report_bytes"] = generate_excel_bytes(blocks, "Payment Report")
            
    if "payment_report_bytes" in st.session_state:
        st.download_button(
            label="Download Payment Report",
            data=st.session_state["payment_report_bytes"],
            file_name="payment_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="secondary"
        )
        
    render_footer("Payment Analytics")
