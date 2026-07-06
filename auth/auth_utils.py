import bcrypt
from database.database import get_connection


def hash_password(password):
    """Convert a plain password into a secure hashed password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password, hashed_password):
    """Verify the entered password with the stored hashed password."""
    return bcrypt.checkpw(password.encode(), hashed_password)

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

def create_user(full_name, username, email, password):
    """Create a new user."""

    hashed_password = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users(full_name, username, email, password)
        VALUES(?,?,?,?)
        """,
        (
            full_name,
            username,
            email,
            hashed_password
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