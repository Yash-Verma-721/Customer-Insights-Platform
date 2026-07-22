import sqlite3
from .connection import get_connection

def create_settlement(cursor, vendor_id, order_item_id, gross, comm_rate, comm_amount, net):
    cursor.execute("""
        INSERT INTO settlements (vendor_id, order_item_id, gross_amount, commission_rate, commission_amount, net_amount, settlement_status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    """, (vendor_id, order_item_id, gross, comm_rate, comm_amount, net))

def check_settlement_exists(cursor, order_item_id):
    cursor.execute("SELECT id FROM settlements WHERE order_item_id = ?", (order_item_id,))
    return cursor.fetchone() is not None

def get_settlement_source_data(cursor, order_item_id):
    cursor.execute("""
        SELECT p.vendor_id, oi.quantity, oi.unit_price, v.commission_rate
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN vendors v ON p.vendor_id = v.id
        WHERE oi.id = ?
    """, (order_item_id,))
    row = cursor.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))

def get_vendor_settlements(cursor, vendor_id):
    cursor.execute("""
        SELECT s.*, o.order_code, p.product_name
        FROM settlements s
        JOIN order_items oi ON s.order_item_id = oi.id
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE s.vendor_id = ?
        ORDER BY s.created_at DESC
    """, (vendor_id,))
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_all_settlements(cursor):
    cursor.execute("""
        SELECT s.*, v.vendor_name, o.order_code, p.product_name
        FROM settlements s
        JOIN vendors v ON s.vendor_id = v.id
        JOIN order_items oi ON s.order_item_id = oi.id
        JOIN orders o ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        ORDER BY s.created_at DESC
    """)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def update_settlement_status(cursor, settlement_id, status, paid_at):
    cursor.execute("""
        UPDATE settlements
        SET settlement_status = ?, paid_at = ?
        WHERE id = ?
    """, (status, paid_at, settlement_id))
