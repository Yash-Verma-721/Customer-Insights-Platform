import sqlite3
import streamlit as st
from .connection import get_connection

def update_dataset_metadata(dataset_name, uploaded_by, upload_time, file_size, total_rows, total_columns, dataset_health, dataset_status, user_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("""
            INSERT INTO user_datasets (user_id, dataset_name, uploaded_by, upload_time, file_size, total_rows, total_columns, dataset_health, dataset_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                dataset_name = excluded.dataset_name,
                uploaded_by = excluded.uploaded_by,
                upload_time = excluded.upload_time,
                file_size = excluded.file_size,
                total_rows = excluded.total_rows,
                total_columns = excluded.total_columns,
                dataset_health = excluded.dataset_health,
                dataset_status = excluded.dataset_status
        """, (user_id, dataset_name, uploaded_by, upload_time, file_size, total_rows, total_columns, dataset_health, dataset_status))
    else:
        cursor.execute("""
            INSERT INTO dataset_metadata (id, dataset_name, uploaded_by, upload_time, file_size, total_rows, total_columns, dataset_health, dataset_status)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                dataset_name = excluded.dataset_name,
                uploaded_by = excluded.uploaded_by,
                upload_time = excluded.upload_time,
                file_size = excluded.file_size,
                total_rows = excluded.total_rows,
                total_columns = excluded.total_columns,
                dataset_health = excluded.dataset_health,
                dataset_status = excluded.dataset_status
        """, (dataset_name, uploaded_by, upload_time, file_size, total_rows, total_columns, dataset_health, dataset_status))
    conn.commit()
    conn.close()
    get_dataset_metadata.clear()

def update_report_metadata(last_report_time, last_report_by, user_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("""
            UPDATE user_datasets
            SET last_report_time = ?, last_report_by = ?
            WHERE user_id = ?
        """, (last_report_time, last_report_by, user_id))
    else:
        cursor.execute("""
            UPDATE dataset_metadata
            SET last_report_time = ?, last_report_by = ?
            WHERE id = 1
        """, (last_report_time, last_report_by))
    conn.commit()
    conn.close()
    get_dataset_metadata.clear()

@st.cache_data
def get_dataset_metadata(user_id=None):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT * FROM user_datasets WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("SELECT * FROM dataset_metadata WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

@st.cache_data
def get_all_published_datasets():
    """Retrieve all published datasets metadata for Managers."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM user_datasets 
        WHERE published_at IS NOT NULL AND pub_dataset_name IS NOT NULL
        ORDER BY published_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def publish_dataset(user_id, df):
    """Publish a working dataset by saving the cleaned dataframe and snapshotting working metadata into pub_ fields."""
    import os
    from datetime import datetime
    
    user_dir = f"datasets/user_{user_id}"
    published_filename = "published_dataset.csv"
    published_path = f"{user_dir}/{published_filename}"
    
    if df is None or df.empty:
        return False, "Cleaned dataframe is empty or not provided."
        
    try:
        df.to_csv(published_path, index=False)
        
        if not os.path.exists(published_path):
            return False, "Failed to create the published dataset file."
        
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_datasets WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return False, "Metadata for active dataset not found."
            
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE user_datasets
            SET 
                dataset_status = 'Published',
                published_at = ?,
                pub_dataset_name = ?,
                pub_file_size = ?,
                pub_total_rows = ?,
                pub_total_columns = ?,
                pub_filename = ?
            WHERE user_id = ?
        """, (
            now_str,
            row['dataset_name'],
            os.path.getsize(published_path),
            len(df),
            len(df.columns),
            published_filename,
            user_id
        ))
        
        conn.commit()
        conn.close()
        get_dataset_metadata.clear()
        get_all_published_datasets.clear()
        return True, "Dataset published successfully."
    except Exception as e:
        return False, str(e)
