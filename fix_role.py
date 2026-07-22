import sys
from database.database import get_connection

def fix_role():
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET role='Admin' WHERE username='demo_admin'")
    conn.commit()
    conn.close()
    print("Fixed role.")

if __name__ == '__main__':
    fix_role()
