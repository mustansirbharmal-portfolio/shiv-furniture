from datetime import datetime, timedelta
from bson import ObjectId
from app.database import get_db
from app.services.email_service import EmailService


class NotificationService:
    
    @staticmethod
    def create_notification(user_id, title, message, notification_type='info', link=None):
        """Create a notification for a user"""
        db = get_db()
        
        notification = {
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'title': title,
            'message': message,
            'type': notification_type,  # info, success, warning, error
            'link': link,
            'is_read': False,
            'created_at': datetime.utcnow()
        }
        
        result = db.notifications.insert_one(notification)
        return str(result.inserted_id)
    
    @staticmethod
    def get_user_notifications(user_id, limit=20, unread_only=False):
        """Get notifications for a user"""
        db = get_db()
        
        query = {'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id}
        if unread_only:
            query['is_read'] = False
        
        notifications = list(db.notifications.find(query).sort('created_at', -1).limit(limit))
        
        return [{
            '_id': str(n['_id']),
            'title': n.get('title'),
            'message': n.get('message'),
            'type': n.get('type'),
            'link': n.get('link'),
            'is_read': n.get('is_read', False),
            'created_at': n.get('created_at').isoformat() if n.get('created_at') else None
        } for n in notifications]
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark a notification as read"""
        db = get_db()
        
        result = db.notifications.update_one(
            {
                '_id': ObjectId(notification_id),
                'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id
            },
            {'$set': {'is_read': True}}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications as read for a user"""
        db = get_db()
        
        result = db.notifications.update_many(
            {'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id},
            {'$set': {'is_read': True}}
        )
        
        return result.modified_count
    
    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications"""
        db = get_db()
        
        return db.notifications.count_documents({
            'user_id': ObjectId(user_id) if isinstance(user_id, str) else user_id,
            'is_read': False
        })
    
    @staticmethod
    def notify_admins(title, message, notification_type='info', link=None):
        """Send notification to all admin users"""
        db = get_db()
        
        admins = db.users.find({'role': 'admin', 'is_active': True})
        
        for admin in admins:
            NotificationService.create_notification(
                admin['_id'],
                title,
                message,
                notification_type,
                link
            )
    
    @staticmethod
    def notify_new_order(order_type, order_number, customer_name, total_amount):
        """Notify admins about a new order"""
        title = f"New {order_type}"
        message = f"{order_number} from {customer_name} - ₹{total_amount:,.2f}"
        NotificationService.notify_admins(title, message, 'success', f'/dashboard/{order_type.lower().replace(" ", "-")}s')
    
    @staticmethod
    def notify_new_payment(payment_number, contact_name, amount, payment_type):
        """Notify admins about a new payment"""
        direction = "received from" if payment_type == 'incoming' else "made to"
        title = "New Payment"
        message = f"{payment_number} - ₹{amount:,.2f} {direction} {contact_name}"
        NotificationService.notify_admins(title, message, 'success', '/dashboard/payments')
    
    @staticmethod
    def send_daily_summary():
        """Send daily summary email to admins"""
        db = get_db()
        
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # Get today's stats
        new_orders = db.sales_orders.count_documents({
            'created_at': {'$gte': yesterday, '$lt': today}
        })
        
        new_invoices = db.customer_invoices.count_documents({
            'created_at': {'$gte': yesterday, '$lt': today}
        })
        
        payments_pipeline = [
            {'$match': {'created_at': {'$gte': yesterday, '$lt': today}}},
            {'$group': {'_id': '$payment_type', 'total': {'$sum': '$amount'}, 'count': {'$sum': 1}}}
        ]
        payments = list(db.payments.aggregate(payments_pipeline))
        
        incoming = next((p for p in payments if p['_id'] == 'incoming'), {'total': 0, 'count': 0})
        outgoing = next((p for p in payments if p['_id'] == 'outgoing'), {'total': 0, 'count': 0})
        
        # Pending invoices
        pending_invoices = db.customer_invoices.count_documents({
            'status': 'posted',
            'payment_status': {'$ne': 'paid'}
        })
        
        pending_amount_pipeline = [
            {'$match': {'status': 'posted', 'payment_status': {'$ne': 'paid'}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount_due'}}}
        ]
        pending_result = list(db.customer_invoices.aggregate(pending_amount_pipeline))
        pending_amount = pending_result[0]['total'] if pending_result else 0
        
        # Get admin emails
        admins = list(db.users.find({'role': 'admin', 'is_active': True}))
        
        for admin in admins:
            try:
                EmailService.send_daily_summary(
                    admin['email'],
                    admin.get('full_name', 'Admin'),
                    {
                        'date': yesterday.strftime('%Y-%m-%d'),
                        'new_orders': new_orders,
                        'new_invoices': new_invoices,
                        'incoming_payments': incoming['count'],
                        'incoming_amount': incoming['total'],
                        'outgoing_payments': outgoing['count'],
                        'outgoing_amount': outgoing['total'],
                        'pending_invoices': pending_invoices,
                        'pending_amount': pending_amount
                    }
                )
            except Exception as e:
                print(f"Failed to send daily summary to {admin['email']}: {e}")
