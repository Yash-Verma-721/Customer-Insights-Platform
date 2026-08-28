import sqlite3
from .connection import get_connection

def log_inventory_movement(cursor, inventory_id, operation_type, quantity_change, notes=""):
    cursor.execute("""
        INSERT INTO inventory_log (inventory_id, operation_type, quantity_change, notes)
        VALUES (?, ?, ?, ?)
    """, (inventory_id, operation_type, quantity_change, notes))

def get_inventory_logs(inventory_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT operation_type, quantity_change, timestamp, notes
        FROM inventory_log
        WHERE inventory_id = ?
        ORDER BY timestamp DESC
    """, (inventory_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_inventory_stock(cursor, product_id):
    cursor.execute("SELECT current_stock FROM inventory WHERE product_id = ?", (product_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def reduce_inventory_stock(cursor, product_id, new_stock):
    cursor.execute("UPDATE inventory SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?", (new_stock, product_id))

def get_vendor_inventory(user_id):
    """Retrieve all inventory records for products owned by a specific vendor."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.id, i.product_id, p.product_name, i.current_stock, i.reorder_level, i.updated_at
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN vendors v ON p.vendor_id = v.id
        WHERE v.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def check_product_ownership(cursor, product_id, user_id):
    cursor.execute("""
        SELECT p.id 
        FROM products p 
        JOIN vendors v ON p.vendor_id = v.id 
        WHERE p.id = ? AND v.user_id = ?
    """, (product_id, user_id))
    return cursor.fetchone() is not None

def insert_inventory(cursor, product_id, current_stock, reorder_level):
    cursor.execute("""
        INSERT INTO inventory (product_id, current_stock, reorder_level, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (product_id, current_stock, reorder_level))
    inventory_id = cursor.lastrowid
    log_inventory_movement(cursor, inventory_id, "Initial Stock", current_stock, "Product added to inventory")

def check_inventory_ownership(cursor, inventory_id, user_id):
    cursor.execute("""
        SELECT i.id 
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN vendors v ON p.vendor_id = v.id
        WHERE i.id = ? AND v.user_id = ?
    """, (inventory_id, user_id))
    return cursor.fetchone() is not None

def update_inventory_record(cursor, inventory_id, current_stock, reorder_level):
    cursor.execute("""
        UPDATE inventory 
        SET current_stock = ?, reorder_level = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (current_stock, reorder_level, inventory_id))

def mark_inventory_damaged(cursor, inventory_id, damaged_qty, notes=""):
    cursor.execute("""
        UPDATE inventory
        SET damaged_stock = damaged_stock + ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (damaged_qty, inventory_id))
    log_inventory_movement(cursor, inventory_id, "Damaged Stock", -damaged_qty, notes)

def get_marketplace_inventory_workflow():
    """Retrieve full marketplace inventory workflow for Admin Operations."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            i.id as inventory_id,
            p.id as product_id,
            v.company_name as company_name,
            v.category as vendor_category,
            p.product_image as "Product Image",
            p.product_name,
            i.current_stock,
            COALESCE(i.damaged_stock, 0) as damaged_stock,
            i.warehouse_name,
            i.reorder_level,
            i.updated_at as last_procurement_date,
            p.status as product_status,
            COALESCE((SELECT SUM(quantity) FROM order_items WHERE product_id = p.id AND item_status IN ('Pending', 'Confirmed', 'Packed')), 0) as reserved_quantity,
            COALESCE((SELECT SUM(quantity) FROM order_items WHERE product_id = p.id), 0) as customer_orders
        FROM inventory i
        JOIN products p ON i.product_id = p.id
        JOIN vendors v ON p.vendor_id = v.id
    """)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        current_stock = d['current_stock']
        reserved = d['reserved_quantity']
        damaged = d['damaged_stock']
        available = current_stock - reserved - damaged
        orders = d['customer_orders']
        received = current_stock + orders
        
        reorder = d['reorder_level']
        
        procurement_status = 'Pending Reorder' if available <= reorder else 'Procured'
        warehouse_status = 'In Stock' if available > 0 else 'Out of Stock'
        stock_status = 'Archived' if d['product_status'] == 'Archived' else ('Critical' if available <= 0 else ('Low' if available <= reorder else 'Healthy'))
        
        result.append({
            'inventory_id': d['inventory_id'],
            'product_id': d['product_id'],
            'Company': d['company_name'],
            'Category': d['vendor_category'],
            'Product Image': d['Product Image'],
            'Product': d['product_name'],
            'Procurement Status': procurement_status,
            'Ordered Quantity': orders,
            'Received Quantity': received,
            'Available Quantity': available,
            'Reserved Quantity': reserved,
            'Warehouse': d.get('warehouse_name', 'Not Assigned'),
            'Warehouse Status': warehouse_status,
            'Last Procurement Date': d['last_procurement_date'],
            'Stock Status': stock_status,
            'reorder_level': reorder
        })
    return result
