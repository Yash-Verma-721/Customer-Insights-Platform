import sqlite3
import streamlit as st
from .connection import get_connection

def get_vendor_id_by_user_id(cursor, user_id):
    cursor.execute("SELECT id FROM vendors WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

@st.cache_data
def get_vendor_profile(user_id):
    """Retrieve vendor profile details by user ID."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_vendor_profile_db(cursor, user_id, vendor_name, owner_name, phone_number, gst_number, address, city, state):
    cursor.execute("""
        UPDATE vendors
        SET vendor_name = ?,
            owner_name = ?,
            phone_number = ?,
            gst_number = ?,
            address = ?,
            city = ?,
            state = ?
        WHERE user_id = ?
    """, (vendor_name, owner_name, phone_number, gst_number, address, city, state, user_id))

def get_all_vendors_admin(cursor):
    """Fetch all vendors for Admin Dashboard."""
    cursor.execute("""
        SELECT v.*, u.username, u.email as user_email
        FROM vendors v
        LEFT JOIN users u ON v.user_id = u.id
        ORDER BY v.created_at DESC
    """)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def update_vendor_status_db(cursor, vendor_id, status, admin_id, rejection_reason, approved_at):
    cursor.execute("""
        UPDATE vendors
        SET vendor_status = ?,
            approved_by = ?,
            rejection_reason = ?,
            approved_at = ?
        WHERE id = ?
    """, (status, admin_id, rejection_reason, approved_at, vendor_id))
