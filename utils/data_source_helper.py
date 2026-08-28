"""
Data Source Helper
==================
Centralizes the Primary/Secondary data source resolution logic.

Architecture:
  PRIMARY  — Marketplace transactional database (always available when seeded)
  SECONDARY — Admin-uploaded CSV/Excel dataset (optional, active when st.session_state["df"] exists)

Usage in every analytics module::

    from utils.data_source_helper import get_analytics_df, render_data_source_banner

    df, source_label, source_name = get_analytics_df(dataset_type="sales")
    render_data_source_banner(source_label, source_name)
    if df is None or df.empty:
        render_empty_state()
        return
"""

import streamlit as st
import pandas as pd
from typing import Tuple, Optional


def get_analytics_df(dataset_type: str = "marketplace") -> Tuple[Optional[pd.DataFrame], str, str]:
    """
    Resolve the active DataFrame for analytics.

    Returns
    -------
    df          : pd.DataFrame or None
    source_label: "Uploaded Dataset" | "Marketplace Database"
    source_name : filename for uploaded, or table description for DB
    """
    # --- SECONDARY source: uploaded dataset takes priority when active ---
    uploaded_df = st.session_state.get("df")
    if uploaded_df is not None and not uploaded_df.empty:
        file_name = st.session_state.get("file_details", {}).get("name", "Uploaded File")
        return uploaded_df, "Uploaded Dataset", file_name

    # --- PRIMARY source: build from marketplace DB ---
    try:
        from services.marketplace_dataset_service import (
            build_sales_dataset,
            build_customer_dataset,
            build_vendor_dataset,
            build_inventory_dataset,
            build_order_dataset,
            build_payment_dataset,
            build_marketplace_dataset,
            has_marketplace_data,
        )

        if not has_marketplace_data():
            return None, "No Data", ""

        builders = {
            "sales":       build_sales_dataset,
            "customer":    build_customer_dataset,
            "vendor":      build_vendor_dataset,
            "inventory":   build_inventory_dataset,
            "order":       build_order_dataset,
            "payment":     build_payment_dataset,
            "marketplace": build_marketplace_dataset,
        }
        builder = builders.get(dataset_type, build_marketplace_dataset)
        df = builder()
        if df.empty:
            return None, "No Data", ""
        return df, "Marketplace Database", "Live Transactional Data"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, "No Data", ""


def render_data_source_banner(source_label: str, source_name: str) -> None:
    """Render a styled info banner showing the active data source."""
    if source_label == "Uploaded Dataset":
        icon = "📂"
        color = "#1d4ed8"
        bg = "#eff6ff"
        border = "#93c5fd"
    elif source_label == "Marketplace Database":
        icon = "🛒"
        color = "#065f46"
        bg = "#ecfdf5"
        border = "#6ee7b7"
    else:
        icon = "⚠️"
        color = "#92400e"
        bg = "#fffbeb"
        border = "#fcd34d"

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border:1px solid {border};
            border-radius:8px;
            padding:10px 16px;
            margin-bottom:16px;
            display:flex;
            align-items:center;
            gap:10px;
        ">
            <span style="font-size:20px;">{icon}</span>
            <div>
                <span style="font-size:12px;color:#6b7280;font-weight:500;text-transform:uppercase;
                    letter-spacing:0.05em;">Active Data Source</span><br>
                <span style="font-size:15px;font-weight:700;color:{color};">{source_label}</span>
                <span style="font-size:13px;color:#6b7280;margin-left:8px;">{source_name}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
