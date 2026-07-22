import streamlit as st
from datetime import datetime
from utils.ui_helpers import render_header, render_help_expander, render_footer, add_session_log, show_smart_notification, branded_spinner
from utils.customer_metrics import detect_customer_columns, detect_marketplace_columns
from utils.etl_pipeline import prepare_dataset, profile_dataset

def show_upload():
    render_header(
        "Dataset Workspace",
        "Upload customer transactions, orders, CRM exports, or engagement data for analysis.",
        "Dataset Workspace"
    )
    
    render_help_expander(
        "Import a customer-level or transaction-level dataset. The workbench profiles the file, "
        "detects likely customer, revenue, date, product, region, and operational columns."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### Upload Customer Dataset")
        uploaded_file = st.file_uploader(
            "Select a CSV or Excel file",
            type=["csv", "xlsx"]
        )
    with col2:
        st.markdown("### Recommended Fields")
        st.info(
            "Accepted formats: CSV, XLSX\n\n"
            "Best columns: customer ID/name, order date, revenue/order amount, product/category, region, and status."
        )

    if uploaded_file is None:
        if "df" in st.session_state:
            show_smart_notification("success", "A dataset is already active in your workspace. You can upload a new one to replace it.")
        else:
            render_footer("Dataset Workspace")
            return

    if uploaded_file is not None:
        # Check if we already loaded this specific file to avoid redundant parsing
        already_loaded = False
        if "file_details" in st.session_state:
            if st.session_state["file_details"].get("name") == uploaded_file.name and \
               st.session_state["file_details"].get("size") == uploaded_file.size and \
               not st.session_state.get("is_cleaned", False):
                already_loaded = True
                
        if not already_loaded:
            with branded_spinner("Uploading dataset..."):
                try:
                    import os
                    from database.database import update_dataset_metadata
                    
                    etl_result = prepare_dataset(uploaded_file)
                    validation = etl_result["validation"]
                    if not validation["is_valid"]:
                        raise ValueError(" ".join(validation["errors"]))
                    df = etl_result["dataframe"]
                    profile = etl_result["profile"]
                    
                    # Save the active dataset
                    user_id = st.session_state.get("user_id")
                    if user_id:
                        user_dir = f"datasets/user_{user_id}"
                        os.makedirs(user_dir, exist_ok=True)
                        dataset_path = f"{user_dir}/active_dataset.csv"
                    else:
                        os.makedirs("datasets", exist_ok=True)
                        dataset_path = "datasets/active_dataset.csv"
                        
                    df.to_csv(dataset_path, index=False)
                    
                    # Store pristine raw copy for Reset functionality
                    st.session_state["raw_df"] = df.copy()
                    st.session_state["df"] = df
                    st.session_state["etl_profile"] = profile
                    st.session_state["pipeline_metrics"] = etl_result["pipeline_metrics"]
                    st.session_state["detected_columns"] = etl_result["detected_columns"]
                    
                    from utils.cache import increment_dataset_version
                    increment_dataset_version()
                    
                    upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    uploader_name = st.session_state.get("full_name", "Analyst")
                    
                    st.session_state["file_details"] = {
                        "name": uploaded_file.name,
                        "type": uploaded_file.type,
                        "size": uploaded_file.size,
                        "time": upload_time,
                        "user": uploader_name
                    }
                    st.session_state["is_cleaned"] = False
                    
                    # Update global metadata in database
                    update_dataset_metadata(
                        dataset_name=uploaded_file.name,
                        uploaded_by=uploader_name,
                        upload_time=upload_time,
                        file_size=uploaded_file.size,
                        total_rows=len(df),
                        total_columns=len(df.columns),
                        dataset_health=profile["readiness_score"],
                        dataset_status="Raw Upload",
                        user_id=user_id
                    )
                    
                    add_session_log(f"Uploaded dataset: {uploaded_file.name} ({len(df)} records)")
                    st.rerun()
                    
                except Exception as e:
                    show_smart_notification("error", f"Unable to process the file: {str(e)}")
                    return

    if "df" in st.session_state:
        df = st.session_state["df"]
        details = st.session_state.get("file_details", {})
        profile = st.session_state.get("etl_profile") or profile_dataset(df)
        detected_columns = st.session_state.get("detected_columns") or {
            "customer": detect_customer_columns(df),
            "marketplace": detect_marketplace_columns(df),
        }
        
        st.markdown("## Dataset Metadata")
        
        meta1, meta2, meta3, meta4, meta5 = st.columns(5)
        with meta1: st.markdown(f"**File Name:**<br>{details.get('name', 'Unknown')}", unsafe_allow_html=True)
        with meta2: st.markdown(f"**Upload Time:**<br>{details.get('time', 'Unknown')}", unsafe_allow_html=True)
        with meta3: 
            size_mb = details.get('size', 0) / (1024 * 1024)
            st.markdown(f"**File Size:**<br>{size_mb:.2f} MB", unsafe_allow_html=True)
        with meta4:
            mem_usage = profile["memory_usage_mb"]
            st.markdown(f"**Memory Usage:**<br>{mem_usage:.2f} MB", unsafe_allow_html=True)
        with meta5:
            st.markdown(f"**Uploaded By:**<br>{details.get('user', 'Unknown')}", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        kpi1, kpi2 = st.columns(2)
        with kpi1:
            st.metric("Records", f"{df.shape[0]:,}", "Loaded Successfully")
        with kpi2:
            st.metric("Available Fields", f"{df.shape[1]:,}", "Ready for Profiling")
            
        st.divider()
        
        st.markdown("## Customer Data Readiness")
        
        missing_vals = profile["missing_values"]
        dup_rows = profile["duplicate_rows"]
        num_cols = profile["numeric_columns"]
        cat_cols = profile["categorical_columns"]
        date_cols = profile["date_columns"]
        
        h1, h2, h3, h4, h5 = st.columns(5)
        
        with h1:
            st.metric("Missing Values", f"{missing_vals:,}")
            st.caption("Gaps in data affecting analysis accuracy.")
        with h2:
            st.metric("Duplicate Rows", f"{dup_rows:,}")
            st.caption("Redundant records that skew metrics.")
        with h3:
            st.metric("Numeric Columns", num_cols)
            st.caption("Features suited for statistical calculation.")
        with h4:
            st.metric("Categorical Columns", cat_cols)
            st.caption("Features suited for segmentation.")
        with h5:
            st.metric("Date Columns", date_cols)
            st.caption("Features suited for timeline trends.")

        st.markdown("### Detected Operational Fields")
        detected = detected_columns["customer"]
        marketplace_detected = detected_columns["marketplace"]
        role_cols = st.columns(4)
        field_roles = [
            ("Vendor", marketplace_detected["vendor"]),
            ("Product", marketplace_detected["product"]),
            ("Stock", marketplace_detected["stock"]),
            ("Order", marketplace_detected["order"]),
        ]
        for idx, (label, values) in enumerate(field_roles):
            with role_cols[idx]:
                if values:
                    st.success(f"{label}: {values[0]}")
                    if len(values) > 1:
                        st.caption(f"Also found: {', '.join(map(str, values[1:3]))}")
                else:
                    st.warning(f"{label}: Not detected")

        st.markdown("### Detected Customer and Revenue Fields")
        role_cols = st.columns(4)
        field_roles = [
            ("Customer", detected["customer"]),
            ("Revenue", detected["revenue"]),
            ("Date", detected["date"]),
            ("Region", detected["region"]),
        ]
        for idx, (label, values) in enumerate(field_roles):
            with role_cols[idx]:
                if values:
                    st.success(f"{label}: {values[0]}")
                    if len(values) > 1:
                        st.caption(f"Also found: {', '.join(map(str, values[1:3]))}")
                else:
                    st.warning(f"{label}: Not detected")
            
        st.divider()
        
        st.markdown("## Dataset Preview")
        with st.expander("Expand to view the first 20 records", expanded=True):
            st.dataframe(df.head(20), use_container_width=True)
            
        st.success("Recommendation: Review data quality in Data Cleaning, then explore Analytics for customer insights.")
        
    render_footer("Dataset Workspace")
