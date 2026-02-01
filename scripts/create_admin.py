"""
Script to create the admin user in the database
Run this script once to set up the admin account
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pymongo import MongoClient
import bcrypt
from datetime import datetime

MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'shiv_furniture_budget')

def create_admin_user():
    client = MongoClient(MONGODB_URI, tls=True, tlsAllowInvalidCertificates=True)
    db = client[MONGODB_DB_NAME]
    
    admin_email = 'adminshivfurniture@gmail.com'
    admin_password = 'admin123'
    
    existing_admin = db.users.find_one({'email': admin_email})
    if existing_admin:
        print(f"Admin user already exists with email: {admin_email}")
        return
    
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
    
    admin_user = {
        'email': admin_email,
        'password_hash': password_hash.decode('utf-8'),
        'full_name': 'Shiv Furniture Admin',
        'role': 'admin',
        'is_active': True,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    }
    
    result = db.users.insert_one(admin_user)
    print(f"Admin user created successfully!")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")
    print(f"User ID: {result.inserted_id}")

if __name__ == '__main__':
    create_admin_user()
