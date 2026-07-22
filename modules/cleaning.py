import streamlit as st
from utils.ui_helpers import (
    render_header, render_empty_state, render_help_expander, 
    render_footer, calculate_readiness_score, get_color_badge, 
    add_session_log, show_smart_notification, branded_spinner
)

def show_cleaning():
    render_header(
        "Customer Data Quality",
        "Resolve missing values, duplicates, and field issues before customer analysis.",
        "Data Cleaning"
    )
    
    render_help_expander(
        "Customer analysis depends on trustworthy records. This page scans for missing values, "
        "duplicate rows, and data type issues that can distort retention, revenue, and segment metrics."
    )

    if "df" not in st.session_state or st.session_state.df is None or st.session_state.df.empty:
        render_empty_state()
        render_footer("Data Cleaning")
        return

    df = st.session_state["df"]
    # Calculate current health metrics
    total_rows = df.shape[0]
    missing_val = df.isnull().sum().sum()
    missing_rows_mask = df.isnull().any(axis=1)
    missing_rows = missing_rows_mask.sum()
    duplicate_rows_mask = df.duplicated()
    duplicates = duplicate_rows_mask.sum()
    rows_to_drop_mask = missing_rows_mask | duplicate_rows_mask
    rows_to_drop = rows_to_drop_mask.sum()
    rows_after_preprocessing = total_rows - rows_to_drop
    rows_to_drop_pct = (rows_to_drop / total_rows * 100) if total_rows else 0

    health_score = calculate_readiness_score(df)
    badge = get_color_badge(health_score)

    # ---------------- DATASET HEALTH SCORE ---------------- #
    st.markdown("## Overall Customer Data Health")
    
    col_score, col_status = st.columns([3, 1])
    with col_score:
        if health_score >= 90:
            st.success(f"**{badge} ({health_score}/100)** - Customer data is ready for analysis.")
            st.progress(health_score / 100.0)
        elif health_score >= 70:
            st.warning(f"**{badge} ({health_score}/100)** - Minor cleaning recommended.")
            st.progress(health_score / 100.0)
        else:
            st.error(f"**{badge} ({health_score}/100)** - Significant cleaning is required before analysis.")
            st.progress(health_score / 100.0)
            
    st.divider()

    # ---------------- PREPROCESSING CHECK ---------------- #
    st.markdown("## Preprocessing Check")

    metric1, metric2, metric3, metric4 = st.columns(4)
    with metric1:
        st.metric("Missing Cells", f"{missing_val:,}")
    with metric2:
        st.metric("Rows With Missing Data", f"{missing_rows:,}")
    with metric3:
        st.metric("Duplicate Rows", f"{duplicates:,}")
    with metric4:
        st.metric("Rows Needing Preprocessing", f"{rows_to_drop:,}")

    if rows_to_drop == 0:
        show_smart_notification("success", "No preprocessing needed. There are no missing rows or duplicate rows.")
        st.write("**Customer Impact:** Records are complete and unique, improving KPI and segment accuracy.")
    else:
        show_smart_notification("warning", "Preprocessing is recommended before you continue.")
        st.caption(
            f"{missing_val:,} missing cells are spread across {missing_rows:,} rows. "
            "A single row can contain more than one missing cell, so the row count can be lower than the missing-cell count."
        )
        show_smart_notification(
            "error",
            f"{rows_to_drop} rows ({rows_to_drop_pct:.1f}% of the dataset) can weaken analysis because they contain missing values or duplicate records."
        )
        show_smart_notification(
            "info",
            f"Preprocessing will keep {rows_after_preprocessing} reliable rows and remove only the records that could distort customer, revenue, retention, and segment metrics."
        )
        st.write(
            "**Why this matters:** Continuing without preprocessing may double-count customers, inflate revenue, "
            "or build segments from incomplete records. Cleaning first gives every later insight a stronger base."
        )
        st.write("**Recommended action:** Preprocess the dataset now, then continue with segment and Business Analytics.")

    st.markdown("### Data Type Review")
    dtype_df = df.dtypes.reset_index()
    dtype_df.columns = ["Feature", "Data Type"]
    st.dataframe(dtype_df, use_container_width=True)
    show_smart_notification("info", "Ensure numeric columns use standard data types such as int or float.")

    st.divider()

    # ---------------- CLEANING CENTER ---------------- #
    st.markdown("## Cleaning Center")
    st.caption("Apply preprocessing to remove rows that are incomplete or duplicated.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(" Preprocess Dataset (Recommended)", use_container_width=True):
            if rows_to_drop > 0:
                with branded_spinner("Removing rows with missing values or duplicates..."):
                    cleaned_df = df.loc[~rows_to_drop_mask].copy()

                    st.session_state["df"] = cleaned_df
                    st.session_state["is_cleaned"] = True
                    
                    from utils.cache import increment_dataset_version
                    increment_dataset_version()
                    
                    msg = (
                        f"{rows_to_drop} rows were removed during preprocessing "
                        f"({missing_rows} rows with missing data, {duplicates} duplicate rows)."
                    )
                    st.session_state["last_action"] = msg
                    add_session_log("Preprocessed dataset")
                st.rerun()
            else:
                st.toast("No preprocessing needed!")

    with col2:
        if st.button(" Reset Dataset", use_container_width=True):
            if "raw_df" in st.session_state:
                with branded_spinner("Resetting dataset..."):
                    st.session_state["df"] = st.session_state["raw_df"].copy()
                    st.session_state["is_cleaned"] = False
                    
                    from utils.cache import increment_dataset_version
                    increment_dataset_version()
                    
                    st.session_state["last_action"] = "Dataset restored to original state."
                    add_session_log("Reset dataset to original state")
                st.rerun()
            else:
                show_smart_notification("error", "Original dataset not found. Please re-upload.")

    # ---------------- CLEANING REPORT ---------------- #
    if "last_action" in st.session_state:
        show_smart_notification("success", st.session_state['last_action'])
        st.markdown("###  Cleaning Report")
        cr1, cr2, cr3 = st.columns(3)
        with cr1:
            raw_rows = st.session_state["raw_df"].shape[0] if "raw_df" in st.session_state else total_rows
            st.metric("Rows Before", raw_rows)
        with cr2:
            st.metric("Rows After", total_rows, delta=total_rows - raw_rows)
        with cr3:
            st.metric("Current Readiness Score", f"{health_score}/100")
            
    st.divider()
    st.info("Recommendation: Once data quality is strong, continue to Segment Analysis and Business Analytics.")
    
    render_footer("Data Cleaning")
