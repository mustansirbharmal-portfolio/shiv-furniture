from datetime import datetime
from bson import ObjectId

class AnalyticalAccount:
    TYPE_INCOME = 'income'
    TYPE_EXPENSE = 'expense'
    TYPE_BOTH = 'both'
    
    ACCOUNT_TYPES = [TYPE_INCOME, TYPE_EXPENSE, TYPE_BOTH]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.code = data.get('code')
            self.name = data.get('name')
            self.description = data.get('description')
            self.account_type = data.get('account_type', self.TYPE_BOTH)
            self.parent_id = data.get('parent_id')
            self.is_archived = data.get('is_archived', False)
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.code = None
            self.name = None
            self.description = None
            self.account_type = self.TYPE_BOTH
            self.parent_id = None
            self.is_archived = False
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'account_type': self.account_type,
            'parent_id': str(self.parent_id) if self.parent_id else None,
            'is_archived': self.is_archived,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'account_type': self.account_type,
            'parent_id': ObjectId(self.parent_id) if self.parent_id else None,
            'is_archived': self.is_archived,
            'created_by': ObjectId(self.created_by) if self.created_by else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return AnalyticalAccount(data)
        return None
