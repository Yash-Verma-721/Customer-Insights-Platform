import bcrypt
from database.database import get_connection


def hash_password(password):
    """Convert a plain password into a secure hashed password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password, hashed_password):
    """Verify the entered password with the stored hashed password."""
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode()
    try:
        return bcrypt.checkpw(password.encode(), hashed_password)
    except ValueError:
        # Fallback for plain-text passwords (e.g., from seed data)
        return password.encode() == hashed_password

def username_exists(username):
    """Check if the username already exists."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )

    user = cursor.fetchone()

    conn.close()

    return user is not None

def email_exists(email):
    """Check if the email already exists."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()

    conn.close()

    return user is not None

def create_user(full_name, username, email, password, role="Business Analyst"):
    """Create a new user."""

    hashed_password = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users(full_name, username, email, password, role)
        VALUES(?,?,?,?,?)
        """,
        (
            full_name,
            username,
            email,
            hashed_password,
            role
        )
    )

    conn.commit()
    conn.close()

def get_user(username):
    """Return user details if username exists."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM users
        WHERE username = ?
        """,
        (username,)
    )

    user = cursor.fetchone()

    conn.close()

    return user

def get_all_users():
    """Return all registered users."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, username, email, role, created_at FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def update_user_role(user_id, new_role):
    """Update a user's role."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()

def company_name_exists(company_name):
    """Check if the company name already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM vendors WHERE company_name = ?", (company_name,))
    vendor = cursor.fetchone()
    conn.close()
    return vendor is not None

def register_vendor(full_name, username, email, password, company_name, category, phone_number=None, gst_number=None, address=None, city=None, state=None, vendor_name=None):
    """Register a new vendor and create a user account."""
    if not vendor_name:
        vendor_name = full_name
        
    if not all([full_name, username, email, password, company_name, category]):
        return False, "All core fields are required."

    if username_exists(username):
        return False, "Username already exists."
        
    if email_exists(email):
        return False, "Email already exists."

    if company_name_exists(company_name):
        return False, "Company name already exists."

    hashed_password = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION")

        cursor.execute(
            """
            INSERT INTO users(full_name, username, email, password, role)
            VALUES(?,?,?,?,?)
            """,
            (full_name, username, email, hashed_password, "Vendor")
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO vendors(user_id, company_name, vendor_name, owner_name, email, phone_number, gst_number, address, city, state, category)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (user_id, company_name, vendor_name, full_name, email, phone_number, gst_number, address, city, state, category)
        )

        conn.commit()
        return True, "Vendor registered successfully."
    except Exception as e:
        conn.rollback()
        return False, f"Registration failed: {str(e)}"
    finally:
        conn.close()