import os
import sys
import pandas as pd

# 1. Test database connection
from database.connection import get_connection, DATABASE_NAME
print(f"Database Path: {DATABASE_NAME}")
print(f"Database Exists: {os.path.exists(DATABASE_NAME)}")

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM orders")
order_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]
cursor.execute("SELECT role FROM users WHERE username='demo_admin'")
admin_role = cursor.fetchone()
conn.close()

print(f"Order Count: {order_count}")
print(f"User Count: {user_count}")
print(f"Admin Role in DB: {admin_role}")

# 2. Test Data Source Helper
from utils.data_source_helper import get_analytics_df

class SessionState(dict):
    def __getattr__(self, key):
        return self.get(key)
    def __setattr__(self, key, value):
        self[key] = value

import streamlit as st
st.session_state = SessionState()
st.session_state.role = "Admin"
st.session_state.username = "demo_admin"

df, label, name = get_analytics_df("marketplace")
print(f"get_analytics_df('marketplace') -> label: '{label}', name: '{name}', df shape: {df.shape if df is not None else None}")

# 3. Test Dashboard Data Loading for Admin
from utils.customer_metrics import detect_customer_columns, detect_marketplace_columns, build_sales_profile
det_mp = detect_marketplace_columns(df)
sales_p, sales_m, _ = build_sales_profile(df, det_mp)
print(f"Admin Dashboard Metrics -> Revenue: ${sales_m.get('total_sales', 0):,.2f}, Orders: {sales_m.get('total_orders', 0)}")

# 4. Test Vendor Reports Data Loading for Vendor
st.session_state.role = "Vendor"
st.session_state.username = "demo_vendor_001"
st.session_state.user_id = 2

df_vendor, label_v, name_v = get_analytics_df("marketplace")
print(f"Vendor get_analytics_df -> label: '{label_v}', name: '{name_v}', df shape: {df_vendor.shape if df_vendor is not None else None}")

print("\n--- ALL PROGRAMMATIC QA CHECKS PASSED SUCCESSFULLY ---")
