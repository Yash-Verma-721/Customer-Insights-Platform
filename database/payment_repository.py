import sqlite3
from .connection import get_connection

def get_pending_order_items(cursor):
    cursor.execute("""
        SELECT oi.order_id, p.vendor_id, v.commission_rate, SUM(oi.quantity * oi.unit_price) as gross_amount
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN vendors v ON p.vendor_id = v.id
        LEFT JOIN payments pay ON oi.order_id = pay.order_id AND p.vendor_id = pay.vendor_id
        WHERE pay.id IS NULL
        GROUP BY oi.order_id, p.vendor_id
    """)
    return cursor.fetchall()

def create_payment(cursor, order_id, vendor_id, gross_amount, commission_amount, net_payout):
    cursor.execute("""
        INSERT INTO payments (order_id, vendor_id, gross_amount, commission_amount, net_payout, status)
        VALUES (?, ?, ?, ?, ?, 'Pending')
    """, (order_id, vendor_id, gross_amount, commission_amount, net_payout))

def get_vendor_payments(user_id):
    """Retrieve all payments for a specific vendor using their user_id."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pay.id, pay.order_id, pay.gross_amount, pay.commission_amount, pay.net_payout, pay.status, pay.settlement_date, o.order_code, o.order_date
        FROM payments pay
        JOIN vendors v ON pay.vendor_id = v.id
        JOIN orders o ON pay.order_id = o.id
        WHERE v.user_id = ?
        ORDER BY o.order_date DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
