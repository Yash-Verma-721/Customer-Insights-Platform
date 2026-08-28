import sqlite3
from datetime import datetime
from .connection import get_connection

VIP_ORDER_THRESHOLD = 5
RETURNING_ORDER_THRESHOLD = 1
AT_RISK_DAYS = 90

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
    
    # Calculate max date for relative inactivity calculation
    max_date = None
    parsed_rows = []
    
    for row in rows:
        lp = row['last_purchase']
        dt = None
        if lp:
            try:
                # Handle standard format
                dt = datetime.fromisoformat(lp.replace('Z', '+00:00'))
            except ValueError:
                try:
                    dt = datetime.strptime(lp.split()[0], '%Y-%m-%d')
                except Exception:
                    pass
                    
        if dt and (max_date is None or dt > max_date):
            max_date = dt
            
        parsed_rows.append((row, dt))
    
    result = []
    for row, dt in parsed_rows:
        d = dict(row)
        
        orders = d['total_orders']
        
        # Determine status
        status = 'Needs Attention'
        
        if dt and max_date and (max_date - dt).days > AT_RISK_DAYS:
            status = 'At Risk'
        elif orders > VIP_ORDER_THRESHOLD:
            status = 'VIP'
        elif orders > RETURNING_ORDER_THRESHOLD:
            status = 'Loyalist'
            
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
