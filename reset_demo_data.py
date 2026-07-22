import time
from database.connection import get_connection
from config.demo_seed import DEMO_PREFIX, DEMO_EMAIL_DOMAIN

def reset_demo_data():
    start_time = time.time()
    
    print("Initializing Database Reset Utility...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Use a single transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # 1. Identify Demo Users deterministically
        cursor.execute(f"""
            SELECT id FROM users 
            WHERE username LIKE '{DEMO_PREFIX}%' 
               OR email LIKE '%@{DEMO_EMAIL_DOMAIN}'
        """)
        demo_user_ids = [row[0] for row in cursor.fetchall()]
        
        if not demo_user_ids:
            print("No demo data found matching the deterministic tags. Exiting.")
            conn.rollback()
            return

        demo_users_placeholder = ','.join('?' * len(demo_user_ids))
        
        # 2. Identify Demo Vendors
        cursor.execute(f"SELECT id FROM vendors WHERE user_id IN ({demo_users_placeholder})", demo_user_ids)
        demo_vendor_ids = [row[0] for row in cursor.fetchall()]
        demo_vendors_placeholder = ','.join('?' * len(demo_vendor_ids)) if demo_vendor_ids else 'NULL'

        # 3. Identify Demo Products
        if demo_vendor_ids:
            cursor.execute(f"SELECT id FROM products WHERE vendor_id IN ({demo_vendors_placeholder})", demo_vendor_ids)
            demo_product_ids = [row[0] for row in cursor.fetchall()]
        else:
            demo_product_ids = []
        demo_products_placeholder = ','.join('?' * len(demo_product_ids)) if demo_product_ids else 'NULL'

        # 4. Identify Demo Orders (by customer email)
        cursor.execute(f"SELECT email FROM users WHERE id IN ({demo_users_placeholder})", demo_user_ids)
        demo_emails = [row[0] for row in cursor.fetchall()]
        demo_emails_placeholder = ','.join('?' * len(demo_emails)) if demo_emails else 'NULL'

        cursor.execute(f"SELECT id FROM orders WHERE customer_email IN ({demo_emails_placeholder})", demo_emails)
        demo_order_ids = [row[0] for row in cursor.fetchall()]
        demo_orders_placeholder = ','.join('?' * len(demo_order_ids)) if demo_order_ids else 'NULL'

        metrics = {
            "Payments Removed": 0,
            "Settlements Removed": 0,
            "Order Items Removed": 0,
            "Orders Removed": 0,
            "Inventory Removed": 0,
            "Products Removed": 0,
            "Vendor Profiles Removed": 0,
            "Users Removed": 0
        }

        # 5. Cascading Deletes
        
        # Payments
        if demo_order_ids or demo_vendor_ids:
            query = f"DELETE FROM payments WHERE order_id IN ({demo_orders_placeholder})"
            if demo_vendor_ids:
                query += f" OR vendor_id IN ({demo_vendors_placeholder})"
            params = demo_order_ids + (demo_vendor_ids if demo_vendor_ids else [])
            cursor.execute(query, params)
            metrics["Payments Removed"] = cursor.rowcount

        # Settlements
        if demo_vendor_ids:
            cursor.execute(f"DELETE FROM settlements WHERE vendor_id IN ({demo_vendors_placeholder})", demo_vendor_ids)
            metrics["Settlements Removed"] = cursor.rowcount

        # Order Items
        if demo_order_ids or demo_product_ids:
            query = f"DELETE FROM order_items WHERE order_id IN ({demo_orders_placeholder})"
            if demo_product_ids:
                query += f" OR product_id IN ({demo_products_placeholder})"
            params = demo_order_ids + (demo_product_ids if demo_product_ids else [])
            cursor.execute(query, params)
            metrics["Order Items Removed"] = cursor.rowcount

        # Orders
        if demo_order_ids:
            cursor.execute(f"DELETE FROM orders WHERE id IN ({demo_orders_placeholder})", demo_order_ids)
            metrics["Orders Removed"] = cursor.rowcount

        # Inventory
        if demo_product_ids:
            cursor.execute(f"DELETE FROM inventory WHERE product_id IN ({demo_products_placeholder})", demo_product_ids)
            metrics["Inventory Removed"] = cursor.rowcount

        # Products
        if demo_product_ids:
            cursor.execute(f"DELETE FROM products WHERE id IN ({demo_products_placeholder})", demo_product_ids)
            metrics["Products Removed"] = cursor.rowcount

        # Vendor Profiles
        if demo_vendor_ids:
            cursor.execute(f"DELETE FROM vendors WHERE id IN ({demo_vendors_placeholder})", demo_vendor_ids)
            metrics["Vendor Profiles Removed"] = cursor.rowcount

        # Users
        if demo_user_ids:
            cursor.execute(f"DELETE FROM users WHERE id IN ({demo_users_placeholder})", demo_user_ids)
            metrics["Users Removed"] = cursor.rowcount
            
        conn.commit()

        print("\n" + "="*40)
        print("Reset Summary")
        print("="*40)
        for k, v in metrics.items():
            print(f"{k}: {v}")
        print("="*40)
        print("Status: SUCCESS")
        print(f"Execution Time: {time.time() - start_time:.2f} seconds")

    except Exception as e:
        conn.rollback()
        print("\n" + "="*40)
        print("Reset Summary")
        print("="*40)
        print("Status: FAILED")
        print(f"Error: {e}")
        print("Rolled back all changes safely.")
        print(f"Execution Time: {time.time() - start_time:.2f} seconds")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_demo_data()
