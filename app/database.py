from pymongo import MongoClient
from flask import current_app, g
import ssl

client = None
db = None

def init_db(app):
    global client, db
    mongo_uri = app.config['MONGODB_URI']
    
    if 'mongodb+srv' in mongo_uri or 'mongodb.net' in mongo_uri:
        client = MongoClient(
            mongo_uri,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
    else:
        client = MongoClient(mongo_uri)
    
    db = client[app.config['MONGODB_DB_NAME']]
    
    create_indexes()
    
    return db

def get_db():
    global db
    return db

def create_indexes():
    global db
    if db is None:
        return
    
    db.users.create_index('email', unique=True)
    db.users.create_index('role')
    
    db.contacts.create_index('email')
    db.contacts.create_index('contact_type')
    db.contacts.create_index('is_archived')
    
    db.products.create_index('sku', unique=True)
    db.products.create_index('category')
    db.products.create_index('is_archived')
    
    db.analytical_accounts.create_index('code', unique=True)
    db.analytical_accounts.create_index('is_archived')
    
    db.budgets.create_index('analytical_account_id')
    db.budgets.create_index([('period_start', 1), ('period_end', 1)])
    db.budgets.create_index('is_archived')
    
    db.auto_analytical_models.create_index('is_active')
    
    db.purchase_orders.create_index('po_number', unique=True)
    db.purchase_orders.create_index('vendor_id')
    db.purchase_orders.create_index('status')
    db.purchase_orders.create_index('created_at')
    
    db.vendor_bills.create_index('bill_number', unique=True)
    db.vendor_bills.create_index('vendor_id')
    db.vendor_bills.create_index('purchase_order_id')
    db.vendor_bills.create_index('payment_status')
    db.vendor_bills.create_index('created_at')
    
    db.sales_orders.create_index('so_number', unique=True)
    db.sales_orders.create_index('customer_id')
    db.sales_orders.create_index('status')
    db.sales_orders.create_index('created_at')
    
    db.customer_invoices.create_index('invoice_number', unique=True)
    db.customer_invoices.create_index('customer_id')
    db.customer_invoices.create_index('sales_order_id')
    db.customer_invoices.create_index('payment_status')
    db.customer_invoices.create_index('created_at')
    
    db.payments.create_index('payment_number', unique=True)
    db.payments.create_index('payment_type')
    db.payments.create_index('contact_id')
    db.payments.create_index('created_at')
    
    db.budget_revisions.create_index('budget_id')
    db.budget_revisions.create_index('created_at')
