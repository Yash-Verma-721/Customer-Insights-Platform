import random
import time
import uuid
from datetime import datetime, timedelta
from faker import Faker

# Use explicit imports from the app structure
from database.connection import get_connection
from database.product_repository import insert_product
from database.inventory_repository import insert_inventory
from database.order_repository import create_order, create_order_item
from database.payment_repository import create_payment
from auth.auth_utils import create_user, register_vendor, get_user

# Service layer
from services.settlement_service import generate_settlement_for_item, mark_settlement_paid

from config.demo_seed import (
    DEMO_SEED,
    NUM_VENDORS,
    NUM_CUSTOMERS,
    PRODUCTS_PER_VENDOR,
    TOTAL_ORDERS,
    ORDER_STATUS_DISTRIBUTION,
    INVENTORY_LEVELS,
    SETTLEMENT_STATUS_DISTRIBUTION,
    DEMO_PREFIX,
    DEMO_EMAIL_DOMAIN
)

def pick_status(distribution_dict):
    """Pick a status based on a percentage distribution dictionary."""
    statuses = list(distribution_dict.keys())
    weights = list(distribution_dict.values())
    return random.choices(statuses, weights=weights, k=1)[0]

def random_date_in_past_days(days=90):
    now = datetime.now()
    random_days = random.randint(0, days)
    random_seconds = random.randint(0, 24*3600)
    return now - timedelta(days=random_days, seconds=random_seconds)

def seed_database():
    start_time = time.time()
    
    print("Initializing Database Seeder...")
    random.seed(DEMO_SEED)
    fake = Faker()
    Faker.seed(DEMO_SEED)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    metrics = {
        "admins": 0,
        "vendors": 0,
        "customers": 0,
        "products": 0,
        "inventory": 0,
        "orders": 0,
        "order_items": 0,
        "settlements": 0,
        "payments": 0,
        "skipped_vendors": 0,
        "skipped_customers": 0
    }
    
    try:
        # Check idempotency limits
        cursor.execute(f"SELECT COUNT(*) FROM users WHERE role = 'Customer' AND username LIKE '{DEMO_PREFIX}%'")
        demo_customer_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM vendors v JOIN users u ON v.user_id = u.id WHERE u.username LIKE '{DEMO_PREFIX}%'")
        demo_vendor_count = cursor.fetchone()[0]
        
        if demo_customer_count >= NUM_CUSTOMERS and demo_vendor_count >= NUM_VENDORS:
            print("Demo data already appears to be present. Exiting to prevent duplicates.")
            print(f"\nExecution Time: {time.time() - start_time:.2f} seconds")
            return
        
        # 1. Admin Account
        if not get_user(f"{DEMO_PREFIX}admin"):
            create_user("Admin User", f"{DEMO_PREFIX}admin", f"{DEMO_PREFIX}admin@{DEMO_EMAIL_DOMAIN}", "Admin@123", role="Admin")
            metrics["admins"] += 1
            
        # 2. Customers
        cursor.execute(f"SELECT id FROM users WHERE role = 'Customer' AND username LIKE '{DEMO_PREFIX}%'")
        existing_customers = cursor.fetchall()
        customers_to_create = max(0, NUM_CUSTOMERS - len(existing_customers))
        
        created_customer_users = []
        for _ in range(customers_to_create):
            f_name = fake.name()
            username = f"{DEMO_PREFIX}customer_{len(existing_customers) + _ + 1:03d}"
            email = f"{username}@{DEMO_EMAIL_DOMAIN}"
            create_user(f_name, username, email, "Customer@123", role="Customer")
            created_customer_users.append({
                "name": f_name,
                "email": email,
                "phone": fake.phone_number()
            })
            metrics["customers"] += 1
        metrics["skipped_customers"] = NUM_CUSTOMERS - customers_to_create
            
        if existing_customers:
            cursor.execute(f"SELECT full_name, email FROM users WHERE role = 'Customer' AND username LIKE '{DEMO_PREFIX}%'")
            for row in cursor.fetchall():
                created_customer_users.append({
                    "name": row[0],
                    "email": row[1],
                    "phone": fake.phone_number()
                })
                
        # 3. Vendors
        cursor.execute(f"""
            SELECT v.id, v.user_id, v.commission_rate 
            FROM vendors v
            JOIN users u ON v.user_id = u.id
            WHERE u.username LIKE '{DEMO_PREFIX}%'
        """)
        existing_vendors = cursor.fetchall()
        vendors_to_create = max(0, NUM_VENDORS - len(existing_vendors))
        
        vendor_categories = ["Electronics", "Fashion", "Home & Kitchen", "Health & Beauty", "Sports"]
        vendor_ids = [v[0] for v in existing_vendors]
        vendor_commission = {v[0]: v[2] for v in existing_vendors}
        
        for i in range(vendors_to_create):
            f_name = fake.name()
            username = f"{DEMO_PREFIX}vendor_{len(existing_vendors) + i + 1:03d}"
            email = f"{username}@{DEMO_EMAIL_DOMAIN}"
            v_name = fake.company()
            cat = random.choice(vendor_categories)
            
            success, msg = register_vendor(
                full_name=f_name,
                username=username,
                email=email,
                password="Vendor@123",
                vendor_name=v_name,
                category=cat,
                phone_number=fake.phone_number(),
                gst_number=fake.bothify(text='??#####????#?Z?'),
                address=fake.street_address(),
                city=fake.city(),
                state=fake.state()
            )
            
            if success:
                # Need to approve the vendor and set commission rate
                cursor.execute("SELECT id, user_id FROM vendors WHERE vendor_name = ?", (v_name,))
                v_row = cursor.fetchone()
                if v_row:
                    v_id = v_row[0]
                    comm_rate = random.randint(5, 15)
                    cursor.execute("""
                        UPDATE vendors 
                        SET vendor_status = 'Approved', status = 'Active', commission_rate = ?
                        WHERE id = ?
                    """, (comm_rate, v_id))
                    vendor_ids.append(v_id)
                    vendor_commission[v_id] = comm_rate
                    metrics["vendors"] += 1
        metrics["skipped_vendors"] = NUM_VENDORS - vendors_to_create
        
        # 4. Products & Inventory
        cursor.execute(f"SELECT COUNT(*) FROM products p JOIN vendors v ON p.vendor_id = v.id JOIN users u ON v.user_id = u.id WHERE u.username LIKE '{DEMO_PREFIX}%'")
        existing_products = cursor.fetchone()[0]
        
        product_list = [] # store to use for orders
        if existing_products < (NUM_VENDORS * PRODUCTS_PER_VENDOR) and vendor_ids:
            for v_id in vendor_ids:
                for _ in range(PRODUCTS_PER_VENDOR):
                    p_name = fake.catch_phrase()
                    price = round(random.uniform(10.0, 500.0), 2)
                    desc = fake.text(max_nb_chars=100)
                    threshold = random.randint(5, 15)
                    
                    cursor.execute("""
                        INSERT INTO products (vendor_id, product_name, category, price, description, status, low_stock_threshold)
                        VALUES (?, ?, ?, ?, ?, 'Active', ?)
                    """, (v_id, p_name, random.choice(vendor_categories), price, desc, threshold))
                    p_id = cursor.lastrowid
                    metrics["products"] += 1
                    
                    stock = random.choice(INVENTORY_LEVELS)
                    cursor.execute("""
                        INSERT INTO inventory (product_id, current_stock, reorder_level, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (p_id, stock, threshold))
                    metrics["inventory"] += 1
                    
                    product_list.append({"id": p_id, "vendor_id": v_id, "price": price, "comm": vendor_commission[v_id]})
        else:
            # Load existing products for order generation
            cursor.execute("SELECT id, vendor_id, price FROM products")
            for row in cursor.fetchall():
                product_list.append({"id": row[0], "vendor_id": row[1], "price": row[2], "comm": vendor_commission.get(row[1], 10)})
                
        conn.commit()

        # 5. Orders & Payments
        # For simplicity and robust transaction handling with settlement service, we will do this partly inside the loop.
        cursor.execute(f"SELECT COUNT(*) FROM orders WHERE customer_email LIKE '%@{DEMO_EMAIL_DOMAIN}'")
        existing_orders = cursor.fetchone()[0]
        orders_to_create = max(0, TOTAL_ORDERS - existing_orders)
        
        order_items_for_settlement = []
        payments_to_create = {}
        
        for _ in range(orders_to_create):
            customer = random.choice(created_customer_users)
            order_code = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            o_date = random_date_in_past_days(90).strftime("%Y-%m-%d %H:%M:%S")
            region = fake.state()
            
            status = pick_status(ORDER_STATUS_DISTRIBUTION)
            pay_status = "Paid" if status in ["Packed", "Shipped", "Delivered"] else "Pending"
            if status == "Cancelled":
                pay_status = "Refunded"
            
            # Select 1 to 3 distinct products
            num_items = random.randint(1, 3)
            selected_products = random.sample(product_list, k=min(num_items, len(product_list)))
            
            total_amount = sum([p['price'] * random.randint(1, 3) for p in selected_products])
            
            # create_order defaults to Pending and Processing. We will overwrite.
            cursor.execute("""
                INSERT INTO orders (
                    order_code, customer_name, customer_email, customer_phone, 
                    order_date, region, payment_status, order_status, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_code, customer['name'], customer['email'], customer['phone'], o_date, region, pay_status, status, total_amount))
            o_id = cursor.lastrowid
            metrics["orders"] += 1
            
            for p in selected_products:
                qty = random.randint(1, 3)
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, item_status, status_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (o_id, p['id'], qty, p['price'], status, o_date))
                oi_id = cursor.lastrowid
                metrics["order_items"] += 1
                
                # Keep track for settlements and payments
                if status == "Delivered":
                    order_items_for_settlement.append(oi_id)
                    
                    gross = p['price'] * qty
                    comm = gross * (p['comm'] / 100.0)
                    net = gross - comm
                    
                    if (o_id, p['vendor_id']) not in payments_to_create:
                        payments_to_create[(o_id, p['vendor_id'])] = {"gross": 0, "comm": 0, "net": 0}
                    
                    payments_to_create[(o_id, p['vendor_id'])]["gross"] += gross
                    payments_to_create[(o_id, p['vendor_id'])]["comm"] += comm
                    payments_to_create[(o_id, p['vendor_id'])]["net"] += net
        
        # Insert aggregate payments for delivered items
        for (o_id, v_id), amts in payments_to_create.items():
            cursor.execute("""
                INSERT INTO payments (order_id, vendor_id, gross_amount, commission_amount, net_payout, status, settlement_date)
                VALUES (?, ?, ?, ?, ?, 'Paid', CURRENT_TIMESTAMP)
            """, (o_id, v_id, amts["gross"], amts["comm"], amts["net"]))
            metrics["payments"] += 1
            
        conn.commit()
        
        # 6. Generate Settlements using the existing service
        # Close current cursor/conn so service can acquire its own cleanly
        conn.close()
        
        # We need admin_id to mark as paid if needed
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT id FROM users WHERE username = '{DEMO_PREFIX}admin'")
        admin_row = cursor.fetchone()
        admin_id = admin_row[0] if admin_row else 1
        conn.close()
        
        for oi_id in order_items_for_settlement:
            success, msg = generate_settlement_for_item(oi_id)
            if success and "already exists" not in msg:
                metrics["settlements"] += 1
                
                # Decide if it should be Paid
                s_status = pick_status(SETTLEMENT_STATUS_DISTRIBUTION)
                if s_status == "Paid":
                    # We need the settlement id
                    conn2 = get_connection()
                    cursor2 = conn2.cursor()
                    cursor2.execute("SELECT id FROM settlements WHERE order_item_id = ?", (oi_id,))
                    s_row = cursor2.fetchone()
                    conn2.close()
                    
                    if s_row:
                        mark_settlement_paid(admin_id, s_row[0])
                        
        # Final Summary
        print("\n" + "="*40)
        print("Demo Data Seeder Summary")
        print("="*40)
        print(f"Admins:             {metrics['admins']}")
        print(f"Vendors:            {metrics['vendors']} (Skipped: {metrics['skipped_vendors']})")
        print(f"Customers:          {metrics['customers']} (Skipped: {metrics['skipped_customers']})")
        print(f"Products:           {metrics['products']}")
        print(f"Inventory Records:  {metrics['inventory']}")
        print(f"Orders:             {metrics['orders']}")
        print(f"Order Items:        {metrics['order_items']}")
        print(f"Settlements:        {metrics['settlements']}")
        print(f"Payments:           {metrics['payments']}")
        print("="*40)
        print("Completed Successfully.")
        print(f"Execution Time: {time.time() - start_time:.2f} seconds")
        
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed_database()
