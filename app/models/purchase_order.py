from datetime import datetime
from bson import ObjectId

class PurchaseOrder:
    STATUS_DRAFT = 'draft'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_RECEIVED = 'received'
    STATUS_CANCELLED = 'cancelled'
    
    STATUSES = [STATUS_DRAFT, STATUS_CONFIRMED, STATUS_RECEIVED, STATUS_CANCELLED]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.po_number = data.get('po_number')
            self.vendor_id = data.get('vendor_id')
            self.order_date = data.get('order_date', datetime.utcnow())
            self.expected_date = data.get('expected_date')
            self.status = data.get('status', self.STATUS_DRAFT)
            self.items = data.get('items', [])
            self.subtotal = data.get('subtotal', 0)
            self.tax_amount = data.get('tax_amount', 0)
            self.total_amount = data.get('total_amount', 0)
            self.notes = data.get('notes')
            self.analytical_account_id = data.get('analytical_account_id')
            self.document_url = data.get('document_url')
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.po_number = None
            self.vendor_id = None
            self.order_date = datetime.utcnow()
            self.expected_date = None
            self.status = self.STATUS_DRAFT
            self.items = []
            self.subtotal = 0
            self.tax_amount = 0
            self.total_amount = 0
            self.notes = None
            self.analytical_account_id = None
            self.document_url = None
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def calculate_totals(self):
        self.subtotal = sum(item.get('subtotal', 0) for item in self.items)
        self.tax_amount = sum(item.get('tax_amount', 0) for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'po_number': self.po_number,
            'vendor_id': str(self.vendor_id) if self.vendor_id else None,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'expected_date': self.expected_date.isoformat() if self.expected_date else None,
            'status': self.status,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'notes': self.notes,
            'analytical_account_id': str(self.analytical_account_id) if self.analytical_account_id else None,
            'document_url': self.document_url,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'po_number': self.po_number,
            'vendor_id': ObjectId(self.vendor_id) if self.vendor_id else None,
            'order_date': self.order_date,
            'expected_date': self.expected_date,
            'status': self.status,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
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
            return PurchaseOrder(data)
        return None
