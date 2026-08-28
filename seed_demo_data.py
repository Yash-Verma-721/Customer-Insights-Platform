import random
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from faker import Faker

from database.connection import get_connection
from auth.auth_utils import create_user
from config.demo_seed import DEMO_PREFIX, DEMO_EMAIL_DOMAIN

NUM_COMPANIES = 120
NUM_CUSTOMERS = 1000
PRODUCTS_TOTAL = 3500
ORDERS_TOTAL = 10000

REALISTIC_CATEGORIES = [
    "Electronics", "Fashion", "Home & Kitchen", "Grocery", "Beauty", 
    "Sports", "Books", "Toys", "Automotive", "Pet Supplies", 
    "Health", "Office", "Tools", "Baby", "Garden", "Music", 
    "Watches", "Jewelry", "Shoes", "Luggage", "Furniture", "Appliances"
]

def get_db():
    conn = get_connection()
    return conn

def cleanup_database(conn):
    cursor = conn.cursor()
    print("Cleaning up existing database...")
    
    tables_to_clear = [
        "inventory_log", "payments", "settlements", "order_items", "orders", 
        "inventory", "products", "vendors"
    ]
    
    for table in tables_to_clear:
        cursor.execute(f"DELETE FROM {table}")
        
    cursor.execute("DELETE FROM users WHERE role IN ('Customer', 'Vendor') OR username LIKE ?", (f"{DEMO_PREFIX}%",))
    
    for table in tables_to_clear:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table,))
        
    print("Database cleanup complete.")

def get_company_distribution(total):
    enterprise = int(total * 0.10)
    medium = int(total * 0.35)
    small = total - enterprise - medium
    return enterprise, medium, small

def generate_companies(conn, fake, num_companies):
    print("Generating companies & vendor reps...")
    cursor = conn.cursor()
    enterprise, medium, small = get_company_distribution(num_companies)
    
    sizes = ['Enterprise'] * enterprise + ['Medium'] * medium + ['Small'] * small
    random.shuffle(sizes)
    
    companies = []
    
    for i in range(num_companies):
        f_name = fake.name()
        username = f"{DEMO_PREFIX}vendor_{i+1:03d}"
        email = f"{username}@{DEMO_EMAIL_DOMAIN}"
        c_name = fake.company()
        cat = random.choice(REALISTIC_CATEGORIES)
        phone = fake.phone_number()
        gst = fake.bothify(text='??#####????#?Z?')
        addr = fake.street_address()
        city = fake.city()
        state = fake.state()
        size = sizes[i]
        
        # User account
        cursor.execute("""
            INSERT INTO users (full_name, username, email, password, role)
            VALUES (?, ?, ?, ?, 'Vendor')
        """, (f_name, username, email, "Vendor@123"))
        user_id = cursor.lastrowid
        
        # Vendor profile
        status = random.choices(["Active", "Suspended", "Pending"], weights=[0.9, 0.05, 0.05])[0]
        v_status = "Approved" if status == "Active" else status
        
        # Rating
        rating = round(random.uniform(3.5, 5.0), 1)
        
        cursor.execute("""
            INSERT INTO vendors (
                user_id, vendor_name, company_name, email, phone_number,
                gst_number, address, city, state, category, status,
                vendor_status, verification_status, commission_rate, rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Verified', ?, ?)
        """, (
            user_id, f_name, c_name, email, phone, gst, addr, city, state, cat, 
            status, v_status, random.randint(5, 15), rating
        ))
        v_id = cursor.lastrowid
        companies.append({"id": v_id, "size": size, "category": cat, "comm": 10})
        
    return companies

def generate_customers(conn, fake, num_customers):
    print("Generating customers...")
    cursor = conn.cursor()
    
    customers = []
    for i in range(num_customers):
        f_name = fake.name()
        username = f"{DEMO_PREFIX}customer_{i+1:04d}"
        email = f"{username}@{DEMO_EMAIL_DOMAIN}"
        phone = fake.phone_number()
        
        cursor.execute("""
            INSERT INTO users (full_name, username, email, password, role)
            VALUES (?, ?, ?, ?, 'Customer')
        """, (f_name, username, email, "Customer@123"))
        c_id = cursor.lastrowid
        
        segment = random.choices(
            ["VIP", "Loyal", "Regular", "Needs Attention", "At Risk"], 
            weights=[0.05, 0.20, 0.50, 0.15, 0.10]
        )[0]
        
        customers.append({
            "id": c_id, "name": f_name, "email": email, "phone": phone, "segment": segment
        })
        
    return customers

def generate_products(conn, fake, companies, total_products):
    print("Generating products and inventory...")
    cursor = conn.cursor()
    
    # Distribute products based on company size
    enterprise = [c for c in companies if c['size'] == 'Enterprise']
    medium = [c for c in companies if c['size'] == 'Medium']
    small = [c for c in companies if c['size'] == 'Small']
    
    products = []
    
    # 50% products to enterprise, 35% to medium, 15% to small
    for c in enterprise:
        target = int((total_products * 0.50) / max(1, len(enterprise)))
        products.extend(_create_products_for_company(cursor, fake, c, target))
    for c in medium:
        target = int((total_products * 0.35) / max(1, len(medium)))
        products.extend(_create_products_for_company(cursor, fake, c, target))
    for c in small:
        target = int((total_products * 0.15) / max(1, len(small)))
        products.extend(_create_products_for_company(cursor, fake, c, max(1, target)))
        
    return products

def _create_products_for_company(cursor, fake, company, count):
    prods = []
    for _ in range(count):
        cat = company['category']
        
        PRODUCT_NAMES = {
            "Electronics": ["Samsung Galaxy S25", "Dell Inspiron", "Logitech Keyboard", "Apple iPad Pro", "Sony PlayStation 5", "Bose QuietComfort 45", "Nintendo Switch", "Amazon Echo Dot", "GoPro HERO11", "Asus ROG Monitor"],
            "Fashion": ["Nike Shoes", "Levi's Jeans", "Ray-Ban Sunglasses", "North Face Jacket", "Calvin Klein T-Shirt", "Adidas Tracksuit", "Under Armour Shorts", "Gucci Belt", "Polo Ralph Lauren Shirt", "Zara Dress"],
            "Home & Kitchen": ["Ninja Blender", "KitchenAid Mixer", "Dyson Vacuum", "Instant Pot", "Nespresso Machine", "Cuisinart Coffee Maker", "Philips Air Fryer", "Pyrex Glass Storage", "OXO Good Grips Utensils", "iRobot Roomba"],
            "Grocery": ["Organic Rice", "Coca-Cola", "Oreo Cookies", "Lays Potato Chips", "Heinz Ketchup", "Nutella", "Quaker Oats", "Tropicana Orange Juice", "Barilla Pasta", "Folgers Coffee"],
            "Beauty": ["Dove Shampoo", "Nivea Cream", "MAC Lipstick", "Estee Lauder Serum", "Clinique Moisturizer", "Maybelline Mascara", "L'Oreal Foundation", "Neutrogena Sunscreen", "Olay Face Wash", "Cetaphil Cleanser"],
            "Sports": ["Wilson Tennis Racket", "Spalding Basketball", "Titleist Golf Balls", "Gatorade Thirst Quencher", "Yeti Rambler", "Nike Yoga Mat", "Rawlings Baseball Glove", "Speedo Swim Goggles", "Babolat Badminton Racket", "Kettler Dumbbells"],
            "Books": ["Atomic Habits", "Clean Code", "The Great Gatsby", "1984", "To Kill a Mockingbird", "Thinking, Fast and Slow", "Sapiens", "The Alchemist", "Harry Potter and the Sorcerer's Stone", "Dune"],
            "Toys": ["LEGO Star Wars", "Barbie Dreamhouse", "Hot Wheels Track", "Nerf Blaster", "Play-Doh Set", "Fisher-Price Piano", "Monopoly Game", "Rubik's Cube", "Melissa & Doug Puzzle", "Funko Pop Figure"],
            "Automotive": ["Michelin Tires", "Castrol Motor Oil", "Bosch Wiper Blades", "Meguiar's Car Wax", "K&N Air Filter", "Armor All Protectant", "Thule Roof Rack", "Pioneer Car Stereo", "Rain-X Windshield Fluid", "Turtle Wax"],
            "Pet Supplies": ["Pedigree Dog Food", "Whiskas Cat Food", "Kong Chew Toy", "Tidy Cats Litter", "Chuckit Ball", "Purina Pro Plan", "Greenies Dental Treats", "Furminator Deshedding Tool", "Nature's Miracle Stain Remover", "Blue Buffalo Cat Treats"],
            "Health": ["Advil Ibuprofen", "Tylenol Extra Strength", "Centrum Multivitamin", "Band-Aid Strips", "Vicks VapoRub", "NyQuil Cold & Flu", "Theragun Massager", "Omron Blood Pressure Monitor", "Listerine Mouthwash", "Crest Whitestrips"],
            "Office": ["Post-it Notes", "Sharpie Markers", "Pilot G2 Pens", "Moleskine Notebook", "Epson Printer", "Hammermill Copy Paper", "Scotch Tape", "Expo Whiteboard Markers", "Herman Miller Chair", "Logitech Mouse"],
            "Tools": ["DeWalt Drill", "Craftsman Wrench Set", "Makita Circular Saw", "Milwaukee Tape Measure", "Stanley Hammer", "Bosch Laser Level", "Dremel Rotary Tool", "Husky Tool Bag", "Ridgid Pipe Wrench", "Knipex Pliers"],
            "Baby": ["Pampers Diapers", "Huggies Wipes", "Johnson's Baby Wash", "Graco Stroller", "Munchkin Bottle Brush", "Dr. Brown's Bottles", "Skip Hop Diaper Bag", "Fisher-Price Swing", "Similac Formula", "Desitin Rash Cream"],
            "Garden": ["Miracle-Gro Potting Mix", "Scotts Turf Builder", "Fiskars Pruning Shears", "Orbit Sprinkler", "Greenworks Lawnmower", "Weber Grill", "Toro Snow Blower", "Roundup Weed Killer", "Husqvarna Chainsaw", "Black+Decker Trimmer"],
            "Music": ["Fender Stratocaster", "Yamaha Keyboard", "Shure SM58 Microphone", "Gibson Les Paul", "Roland Drum Kit", "Casio Piano", "Focusrite Audio Interface", "Martin Acoustic Guitar", "Vic Firth Drumsticks", "Ernie Ball Strings"],
            "Watches": ["Rolex Submariner", "Casio G-Shock", "Seiko 5", "Omega Speedmaster", "Apple Watch", "Garmin Fenix", "Tissot PRX", "Tag Heuer Carrera", "Citizen Eco-Drive", "Timex Weekender"],
            "Jewelry": ["Tiffany Necklace", "Cartier Love Bracelet", "Pandora Charms", "Swarovski Earrings", "David Yurman Ring", "Mejuri Hoops", "Alex and Ani Bangle", "Zales Diamond Studs", "Kendra Scott Pendant", "Blue Nile Engagement Ring"],
            "Shoes": ["Converse Chuck Taylor", "Vans Old Skool", "Adidas Stan Smith", "Nike Air Force 1", "Crocs Classic Clog", "Timberland Boots", "Dr. Martens 1460", "New Balance 574", "Puma Suede", "Reebok Classic"],
            "Luggage": ["Samsonite Spinner", "Away Carry-On", "Travelpro Rollaboard", "Delsey Paris Suitcase", "Rimowa Cabin", "Osprey Backpack", "Tumi Briefcase", "Briggs & Riley Bag", "Victorinox Tote", "SwissGear Duffel"],
            "Furniture": ["IKEA Billy Bookcase", "Ashley Sofa", "West Elm Coffee Table", "Wayfair Rug", "Herman Miller Aeron", "La-Z-Boy Recliner", "Pottery Barn Bed", "Crate & Barrel Dining Chair", "Steelcase Desk", "CB2 Nightstand"],
            "Appliances": ["Whirlpool Refrigerator", "Samsung Washer", "LG Dryer", "GE Microwave", "Bosch Dishwasher", "Frigidaire Oven", "KitchenAid Range", "Dyson Purifier", "Shark Vacuum", "Honeywell Fan"]
        }
        
        modifiers = ["Pro", "Max", "Ultra", "Lite", "Plus", "Edition", "Pack", "Set", "Kit", "Bundle", "Premium", "Classic", "Signature", "Advanced", "Essential", "V2", "2024", "Smart"]
        base_name = random.choice(PRODUCT_NAMES.get(cat, ["Generic Product"]))
        
        if random.random() > 0.5:
            p_name = f"{base_name} {random.choice(modifiers)}"
        else:
            p_name = base_name
            
        sku = f"{cat[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
        cost = round(random.uniform(5.0, 300.0), 2)
        price = round(cost * random.uniform(1.2, 3.0), 2)
        desc = fake.text(max_nb_chars=100)
        threshold = random.randint(5, 20)
        
        # Determine image
        folder_map = {
            "Electronics": "Electronics",
            "Fashion": "Fashion",
            "Home & Kitchen": "Home",
            "Grocery": "Grocery",
            "Beauty": "Beauty",
            "Sports": "Sports",
            "Books": "Books"
        }
        mapped_folder = folder_map.get(cat)
        if mapped_folder:
            img_num = random.randint(1, 15)
            product_image = f"assets/demo_seeds/{mapped_folder}/{mapped_folder.lower()}_{img_num}.jpg"
        else:
            product_image = "assets/placeholder_product.png"

        # Product
        cursor.execute("""
            INSERT INTO products (
                vendor_id, product_name, sku, category, price, cost, description, status, low_stock_threshold, product_image
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
        """, (company['id'], p_name, sku, cat, price, cost, desc, threshold, product_image))
        p_id = cursor.lastrowid
        
        # Inventory
        initial_stock = random.randint(20, 200)
        damaged = random.choices([0, random.randint(1, 5)], weights=[0.8, 0.2])[0]
        
        cursor.execute("""
            INSERT INTO inventory (product_id, current_stock, damaged_stock, reorder_level)
            VALUES (?, ?, ?, ?)
        """, (p_id, initial_stock, damaged, threshold))
        inv_id = cursor.lastrowid
        
        # Log initial stock
        cursor.execute("""
            INSERT INTO inventory_log (inventory_id, operation_type, quantity_change, notes)
            VALUES (?, 'Initial Stock', ?, 'Seed Generation')
        """, (inv_id, initial_stock))
        
        # Generate some procurement history
        if random.random() > 0.5:
            proc_qty = random.randint(10, 50)
            cursor.execute("""
                INSERT INTO inventory_log (inventory_id, operation_type, quantity_change, notes)
                VALUES (?, 'Procurement', ?, 'Supplier Delivery')
            """, (inv_id, proc_qty))
            
            cursor.execute("UPDATE inventory SET current_stock = current_stock + ? WHERE id = ?", (proc_qty, inv_id))
            initial_stock += proc_qty
            
        prods.append({
            "id": p_id, "vendor_id": company['id'], "price": price, 
            "comm": company['comm'], "inv_id": inv_id, "stock": initial_stock - damaged
        })
    return prods

def generate_orders(conn, customers, products, total_orders):
    print("Generating orders, items, payments, and settlements...")
    cursor = conn.cursor()
    
    order_status_dist = {
        "Delivered": 0.70, "Shipped": 0.10, "Processing": 0.05, 
        "Cancelled": 0.10, "Returned": 0.05
    }
    
    now = datetime.now()
    dates = []
    for _ in range(total_orders):
        days_ago = random.randint(0, 365)
        if random.random() < 0.20:
            days_ago = random.randint(0, 60)
        dates.append(now - timedelta(days=days_ago, seconds=random.randint(0, 86400)))
    dates.sort()
    
    segment_weights = {"VIP": 10, "Loyal": 5, "Regular": 2, "Needs Attention": 1, "At Risk": 0.5}
    cust_weights = [segment_weights[c['segment']] for c in customers]
    
    payment_insert_batch = []
    settlement_insert_batch = []
    inventory_log_batch = []
    
    inv_updates = {}
    
    for i in range(total_orders):
        customer = random.choices(customers, weights=cust_weights)[0]
        order_code = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        o_date = dates[i].strftime("%Y-%m-%d %H:%M:%S")
        region = random.choice(["North", "South", "East", "West", "Central"])
        
        status = random.choices(list(order_status_dist.keys()), weights=list(order_status_dist.values()))[0]
        pay_status = "Paid" if status in ["Packed", "Shipped", "Delivered"] else "Pending"
        if status == "Cancelled":
            pay_status = "Refunded"
            
        num_items = random.choices([1, 2, 3, 4, 5], weights=[0.5, 0.3, 0.1, 0.05, 0.05])[0]
        selected_products = random.sample(products, k=min(num_items, len(products)))
        
        valid_items = []
        for p in selected_products:
            qty = random.randint(1, 3)
            if status != "Cancelled":
                current = inv_updates.get(p['inv_id'], p['stock'])
                if current >= qty:
                    inv_updates[p['inv_id']] = current - qty
                    valid_items.append((p, qty))
                    inventory_log_batch.append((p['inv_id'], "Sales", -qty, f"Order {order_code}", o_date))
                elif current > 0:
                    inv_updates[p['inv_id']] = 0
                    valid_items.append((p, current))
                    inventory_log_batch.append((p['inv_id'], "Sales", -current, f"Order {order_code}", o_date))
            else:
                valid_items.append((p, qty))
                
        if not valid_items:
            continue
            
        total_amount = sum(p['price'] * q for p, q in valid_items)
        
        cursor.execute("""
            INSERT INTO orders (order_code, customer_id, customer_name, customer_email, customer_phone, order_date, region, payment_status, order_status, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (order_code, customer['id'], customer['name'], customer['email'], customer['phone'], o_date, region, pay_status, status, total_amount))
        o_id = cursor.lastrowid
        
        vendor_totals = {}
        
        for p, q in valid_items:
            gross = p['price'] * q
            comm_amt = gross * (p['comm'] / 100.0)
            net = gross - comm_amt
            
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, item_status, status_updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (o_id, p['id'], q, p['price'], status, o_date))
            oi_id = cursor.lastrowid
            
            if p['vendor_id'] not in vendor_totals:
                vendor_totals[p['vendor_id']] = {"gross": 0, "comm": 0, "net": 0}
            vendor_totals[p['vendor_id']]["gross"] += gross
            vendor_totals[p['vendor_id']]["comm"] += comm_amt
            vendor_totals[p['vendor_id']]["net"] += net
            
            if status == "Delivered":
                s_status = random.choices(["Paid", "Pending"], weights=[0.8, 0.2])[0]
                settlement_insert_batch.append((p['vendor_id'], oi_id, gross, p['comm'], comm_amt, net, s_status, o_date, o_date if s_status == "Paid" else None))
                
        for v_id, amts in vendor_totals.items():
            payment_insert_batch.append((o_id, v_id, amts['gross'], amts['comm'], amts['net'], pay_status, o_date))
            
    cursor.executemany("""
        INSERT INTO inventory_log (inventory_id, operation_type, quantity_change, notes, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, inventory_log_batch)
    
    for inv_id, new_stock in inv_updates.items():
        cursor.execute("UPDATE inventory SET current_stock = ? WHERE id = ?", (new_stock, inv_id))
        
    cursor.executemany("""
        INSERT INTO payments (order_id, vendor_id, gross_amount, commission_amount, net_payout, status, settlement_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, payment_insert_batch)
    
    cursor.executemany("""
        INSERT INTO settlements (vendor_id, order_item_id, gross_amount, commission_rate, commission_amount, net_amount, settlement_status, created_at, paid_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, settlement_insert_batch)

def verify_dataset(conn):
    print("Running automated validation...")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock < 0")
    if cursor.fetchone()[0] > 0:
        print("WARNING: Found negative inventory!")
        
    cursor.execute("SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT id FROM orders)")
    if cursor.fetchone()[0] > 0:
        print("WARNING: Orphaned order items found!")
        
    cursor.execute("SELECT COUNT(*) FROM payments WHERE order_id NOT IN (SELECT id FROM orders)")
    if cursor.fetchone()[0] > 0:
        print("WARNING: Orphaned payments found!")

def print_summary(conn, start_time):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vendors")
    vendors_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Customer'")
    customers_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    products_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT category) FROM products")
    cats_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM inventory")
    inv_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM inventory_log WHERE operation_type = 'Procurement'")
    proc_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    orders_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM order_items")
    items_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments")
    payments_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM settlements")
    settlements_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_amount) FROM orders WHERE payment_status = 'Paid'")
    total_rev = cursor.fetchone()[0] or 0
    
    cursor.execute("""
        SELECT company_name, (
            SELECT SUM(gross_amount) FROM payments WHERE vendor_id = vendors.id AND status = 'Paid'
        ) as rev
        FROM vendors ORDER BY rev DESC LIMIT 1
    """)
    row = cursor.fetchone()
    highest_rev_company = row[0] if row else "N/A"
    
    cursor.execute("""
        SELECT category, SUM(price) as rev
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        GROUP BY category ORDER BY rev DESC LIMIT 1
    """)
    row = cursor.fetchone()
    top_cat = row[0] if row else "N/A"
    
    cursor.execute("""
        SELECT company_name, (
            SELECT COUNT(*) FROM products WHERE vendor_id = vendors.id
        ) as pc
        FROM vendors ORDER BY pc DESC LIMIT 1
    """)
    row = cursor.fetchone()
    largest_company = row[0] if row else "N/A"
    
    cursor.execute("""
        SELECT p.product_name, i.current_stock
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        ORDER BY i.current_stock ASC LIMIT 3
    """)
    lowest_stock_items = [f"{r[0]} ({r[1]})" for r in cursor.fetchall()]
    lowest_stock_str = ", ".join(lowest_stock_items) if lowest_stock_items else "N/A"
    
    print("\n" + "="*40)
    print("Seed Summary")
    print("="*40)
    print(f"Companies Created:              {vendors_count}")
    print(f"Vendor Representatives Created: {vendors_count}")
    print(f"Customers Created:              {customers_count}")
    print(f"Categories Created:             {cats_count}")
    print(f"Products Created:               {products_count}")
    print(f"Inventory Records Created:      {inv_count}")
    print(f"Procurement Records Created:    {proc_count}")
    print(f"Orders Created:                 {orders_count}")
    print(f"Order Items Created:            {items_count}")
    print(f"Payments Created:               {payments_count}")
    print(f"Settlements Created:            {settlements_count}")
    print("-" * 40)
    print(f"Total Revenue:                  ${total_rev:,.2f}")
    print(f"Average Products / Company:     {products_count/max(1, vendors_count):.1f}")
    print(f"Average Orders / Customer:      {orders_count/max(1, customers_count):.1f}")
    print(f"Largest Company:                {largest_company}")
    print(f"Highest Revenue Company:        {highest_rev_company}")
    print(f"Top Selling Category:           {top_cat}")
    print(f"Lowest Stock Products:          {lowest_stock_str}")
    print("="*40)
    print("Marketplace demo dataset generated successfully.")
    print(f"Execution Time: {time.time() - start_time:.2f} seconds")

def seed_database():
    start_time = time.time()
    print("Initializing Database Seeder...")
    
    random.seed(42)
    fake = Faker()
    Faker.seed(42)
    
    conn = get_db()
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        cleanup_database(conn)
        
        companies = generate_companies(conn, fake, NUM_COMPANIES)
        customers = generate_customers(conn, fake, NUM_CUSTOMERS)
        products = generate_products(conn, fake, companies, PRODUCTS_TOTAL)
        generate_orders(conn, customers, products, ORDERS_TOTAL)
        
        # Admin account
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (f"{DEMO_PREFIX}admin",))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (full_name, username, email, password, role)
                VALUES (?, ?, ?, ?, 'Admin')
            """, ("Admin User", f"{DEMO_PREFIX}admin", f"{DEMO_PREFIX}admin@{DEMO_EMAIL_DOMAIN}", "Admin@123"))
            
        verify_dataset(conn)
        conn.commit()
        
        print_summary(conn, start_time)
        
    except Exception as e:
        conn.rollback()
        print(f"Error seeding database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_database()
