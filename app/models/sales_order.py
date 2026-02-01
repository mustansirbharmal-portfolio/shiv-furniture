from datetime import datetime
from bson import ObjectId

class SalesOrder:
    STATUS_DRAFT = 'draft'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    
    STATUSES = [STATUS_DRAFT, STATUS_CONFIRMED, STATUS_DELIVERED, STATUS_CANCELLED]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.so_number = data.get('so_number')
            self.customer_id = data.get('customer_id')
            self.order_date = data.get('order_date', datetime.utcnow())
            self.delivery_date = data.get('delivery_date')
            self.status = data.get('status', self.STATUS_DRAFT)
            self.items = data.get('items', [])
            self.subtotal = data.get('subtotal', 0)
            self.tax_amount = data.get('tax_amount', 0)
            self.discount_amount = data.get('discount_amount', 0)
            self.total_amount = data.get('total_amount', 0)
            self.shipping_address = data.get('shipping_address', {})
            self.notes = data.get('notes')
            self.analytical_account_id = data.get('analytical_account_id')
            self.document_url = data.get('document_url')
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.so_number = None
            self.customer_id = None
            self.order_date = datetime.utcnow()
            self.delivery_date = None
            self.status = self.STATUS_DRAFT
            self.items = []
            self.subtotal = 0
            self.tax_amount = 0
            self.discount_amount = 0
            self.total_amount = 0
            self.shipping_address = {}
            self.notes = None
            self.analytical_account_id = None
            self.document_url = None
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def calculate_totals(self):
        self.subtotal = sum(item.get('subtotal', 0) for item in self.items)
        self.tax_amount = sum(item.get('tax_amount', 0) for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'so_number': self.so_number,
            'customer_id': str(self.customer_id) if self.customer_id else None,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'status': self.status,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'shipping_address': self.shipping_address,
            'notes': self.notes,
            'analytical_account_id': str(self.analytical_account_id) if self.analytical_account_id else None,
            'document_url': self.document_url,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'so_number': self.so_number,
            'customer_id': ObjectId(self.customer_id) if self.customer_id else None,
            'order_date': self.order_date,
            'delivery_date': self.delivery_date,
            'status': self.status,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'shipping_address': self.shipping_address,
            'notes': self.notes,
            'analytical_account_id': ObjectId(self.analytical_account_id) if self.analytical_account_id else None,
            'document_url': self.document_url,
            'created_by': ObjectId(self.created_by) if self.created_by else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return SalesOrder(data)
        return None
