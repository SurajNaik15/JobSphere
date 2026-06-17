# create_admin.py
# Run this ONCE after setting up the database to create the admin account.
# Usage: python create_admin.py

from werkzeug.security import generate_password_hash
import MySQLdb

# Update these to match your MySQL credentials
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = ''          # Your MySQL password
DB_NAME = 'jobsphere_db'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'   # Change this to a strong password

try:
    conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, passwd=DB_PASS, db=DB_NAME)
    cur = conn.cursor()

    hashed = generate_password_hash(ADMIN_PASSWORD)
    cur.execute("DELETE FROM admins WHERE username = %s", (ADMIN_USERNAME,))
    cur.execute("INSERT INTO admins (username, password) VALUES (%s, %s)", (ADMIN_USERNAME, hashed))
    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Admin created successfully!")
    print(f"   Username: {ADMIN_USERNAME}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"   Login at: http://localhost:5000/admin/login")

except Exception as e:
    print(f"❌ Error: {e}")
    print("Make sure MySQL is running and the database is set up using database/schema.sql")
