import sqlite3
import streamlit as st
from .connection import get_connection

def get_vendor_products(user_id):
    """Retrieve all products for a given vendor (using user_id)."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, COALESCE(i.current_stock, 0) as current_stock 
        FROM products p
        JOIN vendors v ON p.vendor_id = v.id
        LEFT JOIN inventory i ON p.id = i.product_id
        WHERE v.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_product(cursor, vendor_id, product_name, category, price, description, status, low_stock_threshold=10):
    cursor.execute("""
        INSERT INTO products (vendor_id, product_name, category, price, description, status, low_stock_threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (vendor_id, product_name, category, price, description, status, low_stock_threshold))

def update_product_db(cursor, product_id, vendor_id, product_name, category, price, description, status, low_stock_threshold):
    cursor.execute("""
        UPDATE products 
        SET product_name = ?, category = ?, price = ?, description = ?, status = ?, low_stock_threshold = ?
        WHERE id = ? AND vendor_id = ?
    """, (product_name, category, price, description, status, low_stock_threshold, product_id, vendor_id))
    return cursor.rowcount

def update_product_image_db(cursor, product_id, vendor_id, image_path):
    cursor.execute("""
        UPDATE products 
        SET product_image = ?
        WHERE id = ? AND vendor_id = ?
    """, (image_path, product_id, vendor_id))
    return cursor.rowcount

def get_product_image_db(cursor, product_id, vendor_id):
    cursor.execute("""
        SELECT product_image FROM products
        WHERE id = ? AND vendor_id = ?
    """, (product_id, vendor_id))
    row = cursor.fetchone()
    return row[0] if row else None

def delete_product_db(cursor, product_id, vendor_id):
    cursor.execute("DELETE FROM products WHERE id = ? AND vendor_id = ?", (product_id, vendor_id))
    return cursor.rowcount

@st.cache_data
def get_active_marketplace_products():
    """Retrieve all active products that have available inventory for the marketplace catalog."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.product_name, p.category, p.price, p.description, p.status, p.product_image, i.current_stock
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        WHERE p.status = 'Active' AND i.current_stock > 0
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
