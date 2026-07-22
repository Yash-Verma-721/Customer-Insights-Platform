import sqlite3
from .connection import get_connection

def create_order(cursor, order_code, customer_name, customer_email, customer_phone, order_date, region, total_amount):
    cursor.execute("""
        INSERT INTO orders (
            order_code, customer_name, customer_email, customer_phone, 
            order_date, region, payment_status, order_status, total_amount
        ) VALUES (?, ?, ?, ?, ?, ?, 'Pending', 'Processing', ?)
    """, (order_code, customer_name, customer_email, customer_phone, order_date, region, total_amount))
    return cursor.lastrowid

def create_order_item(cursor, order_id, product_id, quantity, unit_price):
    cursor.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?)
    """, (order_id, product_id, quantity, unit_price))

def get_vendor_order_items(cursor, vendor_id):
    cursor.execute("""
        SELECT 
            oi.id as order_item_id,
            o.order_code,
            o.order_date,
            o.customer_name,
            p.product_name,
            oi.quantity,
            (oi.quantity * oi.unit_price) as total_amount,
            o.payment_status,
            oi.item_status,
            oi.status_updated_at,
            o.order_status as global_order_status
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE p.vendor_id = ?
        ORDER BY o.order_date DESC
    """, (vendor_id,))
    
    # Ensuring rows are returned as dictionaries if row_factory wasn't set globally
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def check_order_item_ownership(cursor, order_item_id, vendor_id):
    cursor.execute("""
        SELECT 1 FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.id = ? AND p.vendor_id = ?
    """, (order_item_id, vendor_id))
    return cursor.fetchone() is not None

def update_order_item_status(cursor, order_item_id, new_status, updated_at):
    cursor.execute("""
        UPDATE order_items 
        SET item_status = ?, status_updated_at = ?
        WHERE id = ?
    """, (new_status, updated_at, order_item_id))
