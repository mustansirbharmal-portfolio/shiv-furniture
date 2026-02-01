from datetime import datetime
from bson import ObjectId

class Contact:
    TYPE_CUSTOMER = 'customer'
    TYPE_VENDOR = 'vendor'
    TYPE_BOTH = 'both'
    
    CONTACT_TYPES = [TYPE_CUSTOMER, TYPE_VENDOR, TYPE_BOTH]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.name = data.get('name')
            self.email = data.get('email')
            self.phone = data.get('phone')
            self.contact_type = data.get('contact_type', self.TYPE_CUSTOMER)
            self.company_name = data.get('company_name')
            self.gstin = data.get('gstin')
            self.pan = data.get('pan')
            self.billing_address = data.get('billing_address', {})
            self.shipping_address = data.get('shipping_address', {})
            self.credit_limit = data.get('credit_limit', 0)
            self.payment_terms = data.get('payment_terms', 30)
            self.notes = data.get('notes')
            self.is_archived = data.get('is_archived', False)
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.name = None
            self.email = None
            self.phone = None
            self.contact_type = self.TYPE_CUSTOMER
            self.company_name = None
            self.gstin = None
            self.pan = None
            self.billing_address = {}
            self.shipping_address = {}
            self.credit_limit = 0
            self.payment_terms = 30
            self.notes = None
            self.is_archived = False
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'contact_type': self.contact_type,
            'company_name': self.company_name,
            'gstin': self.gstin,
            'pan': self.pan,
            'billing_address': self.billing_address,
            'shipping_address': self.shipping_address,
            'credit_limit': self.credit_limit,
            'payment_terms': self.payment_terms,
            'notes': self.notes,
            'is_archived': self.is_archived,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'contact_type': self.contact_type,
            'company_name': self.company_name,
            'gstin': self.gstin,
            'pan': self.pan,
            'billing_address': self.billing_address,
            'shipping_address': self.shipping_address,
            'credit_limit': self.credit_limit,
            'payment_terms': self.payment_terms,
            'notes': self.notes,
            'is_archived': self.is_archived,
            'created_by': ObjectId(self.created_by) if self.created_by else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return Contact(data)
        return None
