import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_NAME = os.path.join(BASE_DIR, "database", "users.db")

def get_connection():
    """Create and return a database connection using absolute path."""
    return sqlite3.connect(DATABASE_NAME)
