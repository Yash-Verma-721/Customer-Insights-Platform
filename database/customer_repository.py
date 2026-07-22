import sqlite3
from .connection import get_connection

def get_marketplace_customers():
    """Retrieve customer CRM data aggregated from orders."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COALESCE(customer_name, 'Unknown Customer') as customer_name,
            COALESCE(customer_email, 'No Email') as customer_email,
            COALESCE(customer_phone, 'No Phone') as customer_phone,
            COUNT(DISTINCT order_code) as total_orders,
            SUM(total_amount) as total_spend,
            MAX(order_date) as last_purchase
        FROM orders
        GROUP BY customer_email
        ORDER BY total_spend DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        d = dict(row)
        
        # Simple customer status based on total orders
        orders = d['total_orders']
        if orders > 5:
            status = 'VIP'
        elif orders > 1:
            status = 'Returning'
        else:
            status = 'New'
            
        result.append({
            'Customer Name': d['customer_name'],
            'Email': d['customer_email'],
            'Phone': d['customer_phone'],
            'Total Orders': orders,
            'Total Spend': d['total_spend'],
            'Last Purchase': d['last_purchase'],
            'Customer Status': status
        })
        
    return result
