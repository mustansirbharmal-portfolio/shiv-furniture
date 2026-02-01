"""
Scheduler for background tasks like daily summary emails and notifications.
Run this separately: python scheduler.py
"""
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.services.notification_service import NotificationService

app = create_app()

def send_daily_summary():
    """Send daily summary email to all admins"""
    with app.app_context():
        print(f"[{datetime.now()}] Running daily summary job...")
        try:
            NotificationService.send_daily_summary()
            print(f"[{datetime.now()}] Daily summary sent successfully")
        except Exception as e:
            print(f"[{datetime.now()}] Error sending daily summary: {e}")

def check_overdue_invoices():
    """Check for overdue invoices and send notifications"""
    with app.app_context():
        print(f"[{datetime.now()}] Checking overdue invoices...")
        try:
            from app.database import get_db
            db = get_db()
            
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Find overdue invoices
            overdue_invoices = list(db.customer_invoices.find({
                'status': 'posted',
                'payment_status': {'$ne': 'paid'},
                'due_date': {'$lt': today}
            }))
            
            if overdue_invoices:
                # Notify admins about overdue invoices
                count = len(overdue_invoices)
                total_overdue = sum(inv.get('amount_due', 0) for inv in overdue_invoices)
                
                NotificationService.notify_admins(
                    'Overdue Invoices Alert',
                    f'{count} invoices with ₹{total_overdue:,.2f} are overdue',
                    'warning',
                    '/dashboard/invoices'
                )
                print(f"[{datetime.now()}] Found {count} overdue invoices")
            else:
                print(f"[{datetime.now()}] No overdue invoices")
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking overdue invoices: {e}")

def check_low_stock():
    """Check for low stock products and notify"""
    with app.app_context():
        print(f"[{datetime.now()}] Checking low stock...")
        try:
            from app.database import get_db
            db = get_db()
            
            # Find products with low stock (below reorder level)
            low_stock = list(db.products.find({
                'is_active': True,
                '$expr': {'$lt': ['$stock_quantity', '$reorder_level']}
            }))
            
            if low_stock:
                count = len(low_stock)
                NotificationService.notify_admins(
                    'Low Stock Alert',
                    f'{count} products are below reorder level',
                    'warning',
                    '/dashboard/products'
                )
                print(f"[{datetime.now()}] Found {count} low stock products")
            else:
                print(f"[{datetime.now()}] No low stock products")
                
        except Exception as e:
            print(f"[{datetime.now()}] Error checking low stock: {e}")

# Schedule jobs
# Daily summary at 8:00 AM
schedule.every().day.at("08:00").do(send_daily_summary)

# Check overdue invoices every hour
schedule.every().hour.do(check_overdue_invoices)

# Check low stock every 6 hours
schedule.every(6).hours.do(check_low_stock)

if __name__ == '__main__':
    print("=" * 50)
    print("Shiv Furniture ERP - Background Scheduler")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print("\nScheduled jobs:")
    print("  - Daily summary: 8:00 AM every day")
    print("  - Overdue invoices check: Every hour")
    print("  - Low stock check: Every 6 hours")
    print("\nPress Ctrl+C to stop")
    print("=" * 50)
    
    # Run pending jobs immediately on start (optional)
    # check_overdue_invoices()
    # check_low_stock()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
