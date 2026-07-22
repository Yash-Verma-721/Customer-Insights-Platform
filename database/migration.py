import sqlite3
from .connection import get_connection

def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT DEFAULT 'Manager'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_metadata(
            id INTEGER PRIMARY KEY CHECK (id = 1),
            dataset_name TEXT,
            uploaded_by TEXT,
            upload_time TEXT,
            file_size INTEGER,
            total_rows INTEGER,
            total_columns INTEGER,
            dataset_health INTEGER,
            dataset_status TEXT,
            last_report_time TEXT,
            last_report_by TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_datasets(
            user_id INTEGER PRIMARY KEY,
            dataset_name TEXT,
            uploaded_by TEXT,
            upload_time TEXT,
            file_size INTEGER,
            total_rows INTEGER,
            total_columns INTEGER,
            dataset_health INTEGER,
            dataset_status TEXT,
            last_report_time TEXT,
            last_report_by TEXT
        )
    """)

    create_marketplace_tables(cursor)

    conn.commit()
    conn.close()

def create_marketplace_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            vendor_name TEXT NOT NULL,
            owner_name TEXT,
            email TEXT UNIQUE,
            phone_number TEXT,
            gst_number TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            category TEXT,
            status TEXT DEFAULT 'Active',
            verification_status TEXT DEFAULT 'Pending',
            vendor_status TEXT DEFAULT 'Pending',
            approved_at DATETIME,
            approved_by INTEGER,
            rejection_reason TEXT,
            commission_rate REAL DEFAULT 0,
            rating REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            product_name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category TEXT,
            price REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            description TEXT,
            status TEXT DEFAULT 'Active',
            product_image TEXT,
            low_stock_threshold INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE,
            customer_id TEXT,
            order_date TEXT,
            region TEXT,
            payment_status TEXT,
            order_status TEXT,
            total_amount REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            return_status TEXT DEFAULT 'No',
            delivery_days REAL DEFAULT 0,
            item_status TEXT DEFAULT 'Pending',
            status_updated_at DATETIME,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)
        
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settlements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            order_item_id INTEGER UNIQUE,
            gross_amount REAL,
            commission_rate REAL,
            commission_amount REAL,
            net_amount REAL,
            settlement_status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at DATETIME,
            FOREIGN KEY(vendor_id) REFERENCES vendors(id),
            FOREIGN KEY(order_item_id) REFERENCES order_items(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER UNIQUE,
            current_stock INTEGER DEFAULT 0,
            reorder_level INTEGER DEFAULT 10,
            lead_time_days INTEGER DEFAULT 7,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            vendor_id INTEGER,
            gross_amount REAL DEFAULT 0,
            commission_amount REAL DEFAULT 0,
            net_payout REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            settlement_date TIMESTAMP,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(vendor_id) REFERENCES vendors(id)
        )
    """)

def migrate_database():
    conn = get_connection()
    cursor = conn.cursor()
    create_marketplace_tables(cursor)
    conn.commit()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Manager'")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    from core.logger import get_logger
    logger = get_logger(__name__)

    cursor.execute("PRAGMA table_info(vendors)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    if "user_id" not in existing_columns:
        try:
            cursor.execute("""
                CREATE TABLE vendors_new(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    vendor_name TEXT NOT NULL,
                    owner_name TEXT,
                    email TEXT UNIQUE,
                    phone_number TEXT,
                    gst_number TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    category TEXT,
                    status TEXT DEFAULT 'Active',
                    verification_status TEXT DEFAULT 'Pending',
                    vendor_status TEXT DEFAULT 'Pending',
                    approved_at DATETIME,
                    approved_by INTEGER,
                    rejection_reason TEXT,
                    commission_rate REAL DEFAULT 0,
                    rating REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("PRAGMA table_info(vendors_new)")
            new_columns = [col[1] for col in cursor.fetchall()]
            
            common_cols = [c for c in existing_columns if c in new_columns]
            cols_csv = ", ".join(common_cols)
            
            cursor.execute(f"INSERT INTO vendors_new ({cols_csv}) SELECT {cols_csv} FROM vendors")
            
            cursor.execute("DROP TABLE vendors")
            cursor.execute("ALTER TABLE vendors_new RENAME TO vendors")
            
            conn.commit()
            logger.info("Successfully rebuilt 'vendors' table to include 'user_id' column.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to rebuild 'vendors' table: {str(e)}", exc_info=True)
        
    for col in ["phone_number", "gst_number", "address", "city", "state", "vendor_status", "approved_at", "approved_by", "rejection_reason"]:
        try:
            if col == "vendor_status":
                cursor.execute(f"ALTER TABLE vendors ADD COLUMN {col} TEXT DEFAULT 'Pending'")
            elif col == "approved_by":
                cursor.execute(f"ALTER TABLE vendors ADD COLUMN {col} INTEGER")
            else:
                cursor.execute(f"ALTER TABLE vendors ADD COLUMN {col} TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
            
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN description TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN product_image TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN low_stock_threshold INTEGER DEFAULT 10")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    for col in ["customer_name", "customer_email", "customer_phone"]:
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col} TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        
    try:
        cursor.execute("ALTER TABLE user_datasets ADD COLUMN published_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE order_items ADD COLUMN item_status TEXT DEFAULT 'Pending'")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE order_items ADD COLUMN status_updated_at DATETIME")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    for col in ["pub_dataset_name", "pub_filename", "pub_published_at"]:
        try:
            cursor.execute(f"ALTER TABLE user_datasets ADD COLUMN {col} TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
            
    for col in ["pub_file_size", "pub_total_rows", "pub_total_columns"]:
        try:
            cursor.execute(f"ALTER TABLE user_datasets ADD COLUMN {col} INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass
            
    try:
        cursor.execute("ALTER TABLE dataset_metadata ADD COLUMN published_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("""
            UPDATE user_datasets 
            SET 
                pub_dataset_name = dataset_name,
                pub_file_size = file_size,
                pub_total_rows = total_rows,
                pub_total_columns = total_columns,
                pub_filename = 'published_dataset.csv'
            WHERE published_at IS NOT NULL AND pub_dataset_name IS NULL
        """)
        conn.commit()
    except sqlite3.Error:
        pass
        
    finally:
        conn.close()
