from datetime import datetime
from bson import ObjectId

class Payment:
    TYPE_INCOMING = 'incoming'
    TYPE_OUTGOING = 'outgoing'
    
    METHOD_CASH = 'cash'
    METHOD_BANK_TRANSFER = 'bank_transfer'
    METHOD_CHEQUE = 'cheque'
    METHOD_UPI = 'upi'
    METHOD_CARD = 'card'
    METHOD_ONLINE = 'online'
    
    PAYMENT_TYPES = [TYPE_INCOMING, TYPE_OUTGOING]
    PAYMENT_METHODS = [METHOD_CASH, METHOD_BANK_TRANSFER, METHOD_CHEQUE, METHOD_UPI, METHOD_CARD, METHOD_ONLINE]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.payment_number = data.get('payment_number')
            self.payment_type = data.get('payment_type')
            self.payment_method = data.get('payment_method', self.METHOD_BANK_TRANSFER)
            self.contact_id = data.get('contact_id')
            self.invoice_id = data.get('invoice_id')
            self.bill_id = data.get('bill_id')
            self.payment_date = data.get('payment_date', datetime.utcnow())
            self.amount = data.get('amount', 0)
            self.reference_number = data.get('reference_number')
            self.notes = data.get('notes')
            self.is_reconciled = data.get('is_reconciled', False)
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.payment_number = None
            self.payment_type = None
            self.payment_method = self.METHOD_BANK_TRANSFER
            self.contact_id = None
            self.invoice_id = None
            self.bill_id = None
            self.payment_date = datetime.utcnow()
            self.amount = 0
            self.reference_number = None
            self.notes = None
            self.is_reconciled = False
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'payment_number': self.payment_number,
            'payment_type': self.payment_type,
            'payment_method': self.payment_method,
            'contact_id': str(self.contact_id) if self.contact_id else None,
            'invoice_id': str(self.invoice_id) if self.invoice_id else None,
            'bill_id': str(self.bill_id) if self.bill_id else None,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': self.amount,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'is_reconciled': self.is_reconciled,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'payment_number': self.payment_number,
            'payment_type': self.payment_type,
            'payment_method': self.payment_method,
            'contact_id': ObjectId(self.contact_id) if self.contact_id else None,
            'invoice_id': ObjectId(self.invoice_id) if self.invoice_id else None,
            'bill_id': ObjectId(self.bill_id) if self.bill_id else None,
            'payment_date': self.payment_date,
            'amount': self.amount,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'is_reconciled': self.is_reconciled,
            'created_by': ObjectId(self.created_by) if self.created_by else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return Payment(data)
        return None
