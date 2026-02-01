from datetime import datetime
from bson import ObjectId

class VendorBill:
    STATUS_DRAFT = 'draft'
    STATUS_POSTED = 'posted'
    STATUS_CANCELLED = 'cancelled'
    
    PAYMENT_STATUS_NOT_PAID = 'not_paid'
    PAYMENT_STATUS_PARTIALLY_PAID = 'partially_paid'
    PAYMENT_STATUS_PAID = 'paid'
    
    STATUSES = [STATUS_DRAFT, STATUS_POSTED, STATUS_CANCELLED]
    PAYMENT_STATUSES = [PAYMENT_STATUS_NOT_PAID, PAYMENT_STATUS_PARTIALLY_PAID, PAYMENT_STATUS_PAID]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.bill_number = data.get('bill_number')
            self.vendor_bill_number = data.get('vendor_bill_number')
            self.vendor_id = data.get('vendor_id')
            self.purchase_order_id = data.get('purchase_order_id')
            self.bill_date = data.get('bill_date', datetime.utcnow())
            self.due_date = data.get('due_date')
            self.status = data.get('status', self.STATUS_DRAFT)
            self.payment_status = data.get('payment_status', self.PAYMENT_STATUS_NOT_PAID)
            self.items = data.get('items', [])
            self.subtotal = data.get('subtotal', 0)
            self.tax_amount = data.get('tax_amount', 0)
            self.total_amount = data.get('total_amount', 0)
            self.amount_paid = data.get('amount_paid', 0)
            self.amount_due = data.get('amount_due', 0)
            self.notes = data.get('notes')
            self.analytical_account_id = data.get('analytical_account_id')
            self.document_url = data.get('document_url')
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.bill_number = None
            self.vendor_bill_number = None
            self.vendor_id = None
            self.purchase_order_id = None
            self.bill_date = datetime.utcnow()
            self.due_date = None
            self.status = self.STATUS_DRAFT
            self.payment_status = self.PAYMENT_STATUS_NOT_PAID
            self.items = []
            self.subtotal = 0
            self.tax_amount = 0
            self.total_amount = 0
            self.amount_paid = 0
            self.amount_due = 0
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
        self.amount_due = self.total_amount - self.amount_paid
    
    def update_payment_status(self):
        if self.amount_paid >= self.total_amount:
            self.payment_status = self.PAYMENT_STATUS_PAID
        elif self.amount_paid > 0:
            self.payment_status = self.PAYMENT_STATUS_PARTIALLY_PAID
        else:
            self.payment_status = self.PAYMENT_STATUS_NOT_PAID
        self.amount_due = self.total_amount - self.amount_paid
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'bill_number': self.bill_number,
            'vendor_bill_number': self.vendor_bill_number,
            'vendor_id': str(self.vendor_id) if self.vendor_id else None,
            'purchase_order_id': str(self.purchase_order_id) if self.purchase_order_id else None,
            'bill_date': self.bill_date.isoformat() if self.bill_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'payment_status': self.payment_status,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'amount_paid': self.amount_paid,
            'amount_due': self.amount_due,
            'notes': self.notes,
            'analytical_account_id': str(self.analytical_account_id) if self.analytical_account_id else None,
            'document_url': self.document_url,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'bill_number': self.bill_number,
            'vendor_bill_number': self.vendor_bill_number,
            'vendor_id': ObjectId(self.vendor_id) if self.vendor_id else None,
            'purchase_order_id': ObjectId(self.purchase_order_id) if self.purchase_order_id else None,
            'bill_date': self.bill_date,
            'due_date': self.due_date,
            'status': self.status,
            'payment_status': self.payment_status,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'amount_paid': self.amount_paid,
            'amount_due': self.amount_due,
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
            return VendorBill(data)
        return None
