import streamlit as st
import os
from database.database import get_all_published_datasets
from utils.ui_helpers import render_header, render_empty_state, render_footer

def show_library():
    render_header(
        "Published Dataset Library",
        "Browse and select from officially published customer datasets.",
        "Dataset Library"
    )

    datasets = get_all_published_datasets()
    
    # Filter datasets that physically exist
    valid_datasets = []
    for d in datasets:
        file_path = f"datasets/user_{d['user_id']}/published_dataset.csv"
        if os.path.exists(file_path):
            d["file_path"] = file_path
            valid_datasets.append(d)

    if not valid_datasets:
        st.info("No published datasets are currently available. Analysts must publish their working datasets first.")
        render_footer("Dataset Library")
        return

    st.markdown("### Available Published Datasets")
    
    for d in valid_datasets:
        with st.container():
            st.markdown(f"""
            <div style="
                background-color: #1e293b; 
                border: 1px solid #334155; 
                padding: 20px; 
                border-radius: 10px; 
                margin-bottom: -60px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                position: relative;
                z-index: 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="margin: 0; color: #f8fafc; font-size: 1.25rem; font-weight: 600;">{d.get('pub_dataset_name', 'Unknown Dataset')}</h3>
                    <span style="background-color: rgba(34, 197, 94, 0.15); color: #4ade80; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; border: 1px solid rgba(34, 197, 94, 0.3); display: flex; align-items: center; gap: 4px;">
                        🟢 Published
                    </span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 18px; color: #94a3b8; font-size: 0.9rem;">
                    <div><strong style="color: #cbd5e1;">👤 By:</strong> {d.get('uploaded_by', 'Unknown')}</div>
                    <div><strong style="color: #cbd5e1;">📅 Date:</strong> {d.get('published_at', 'Unknown')}</div>
                    <div><strong style="color: #cbd5e1;">📊 Rows:</strong> {d.get('pub_total_rows', 0):,}</div>
                    <div><strong style="color: #cbd5e1;">📏 Cols:</strong> {d.get('pub_total_columns', 0):,}</div>
                </div>
                <div style="height: 45px;"></div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([5, 2, 2])
            with col3:
                if st.button("Open Dataset", key=f"open_{d['user_id']}", use_container_width=True, type="primary"):
                    st.session_state.selected_published_user_id = d['user_id']
                    st.session_state.current_nav = "Customer Overview"
                    
                    # Clear existing dataset state to force reload
                    keys_to_clear = ["df", "raw_df", "profile", "metrics", "detected_columns", "file_details", "is_cleaned"]
                    for k in keys_to_clear:
                        if k in st.session_state:
                            del st.session_state[k]
                    
                    st.rerun()
                
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    render_footer("Dataset Library")
