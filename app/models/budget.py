from datetime import datetime
from bson import ObjectId

class Budget:
    TYPE_INCOME = 'income'
    TYPE_EXPENSE = 'expense'
    
    BUDGET_TYPES = [TYPE_INCOME, TYPE_EXPENSE]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.name = data.get('name')
            self.analytical_account_id = data.get('analytical_account_id')
            self.budget_type = data.get('budget_type', self.TYPE_EXPENSE)
            self.period_start = data.get('period_start')
            self.period_end = data.get('period_end')
            self.budgeted_amount = data.get('budgeted_amount', 0)
            self.description = data.get('description')
            self.is_archived = data.get('is_archived', False)
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.name = None
            self.analytical_account_id = None
            self.budget_type = self.TYPE_EXPENSE
            self.period_start = None
            self.period_end = None
            self.budgeted_amount = 0
            self.description = None
            self.is_archived = False
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'name': self.name,
            'analytical_account_id': str(self.analytical_account_id) if self.analytical_account_id else None,
            'budget_type': self.budget_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'budgeted_amount': self.budgeted_amount,
            'description': self.description,
            'is_archived': self.is_archived,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'name': self.name,
            'analytical_account_id': ObjectId(self.analytical_account_id) if self.analytical_account_id else None,
            'budget_type': self.budget_type,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'budgeted_amount': self.budgeted_amount,
            'description': self.description,
            'is_archived': self.is_archived,
            'created_by': ObjectId(self.created_by) if self.created_by else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return Budget(data)
        return None


class BudgetRevision:
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.budget_id = data.get('budget_id')
            self.previous_amount = data.get('previous_amount', 0)
            self.new_amount = data.get('new_amount', 0)
            self.reason = data.get('reason')
            self.revised_by = data.get('revised_by')
            self.created_at = data.get('created_at', datetime.utcnow())
        else:
            self._id = None
            self.budget_id = None
            self.previous_amount = 0
            self.new_amount = 0
            self.reason = None
            self.revised_by = None
            self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'budget_id': str(self.budget_id) if self.budget_id else None,
            'previous_amount': self.previous_amount,
            'new_amount': self.new_amount,
            'reason': self.reason,
            'revised_by': str(self.revised_by) if self.revised_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_db_dict(self):
        return {
            'budget_id': ObjectId(self.budget_id) if self.budget_id else None,
            'previous_amount': self.previous_amount,
            'new_amount': self.new_amount,
            'reason': self.reason,
            'revised_by': ObjectId(self.revised_by) if self.revised_by else None,
            'created_at': self.created_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return BudgetRevision(data)
        return None
