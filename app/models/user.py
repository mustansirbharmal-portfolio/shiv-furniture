from datetime import datetime
from bson import ObjectId
import bcrypt

class User:
    ROLE_ADMIN = 'admin'
    ROLE_PORTAL_USER = 'portal_user'
    ROLE_VENDOR = 'vendor'
    
    ROLES = [ROLE_ADMIN, ROLE_PORTAL_USER, ROLE_VENDOR]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.email = data.get('email')
            self.password_hash = data.get('password_hash')
            self.full_name = data.get('full_name')
            self.phone = data.get('phone', '')
            self.role = data.get('role', self.ROLE_PORTAL_USER)
            self.contact_id = data.get('contact_id')
            self.is_active = data.get('is_active', True)
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
            self.last_login = data.get('last_login')
            self.password_reset_token = data.get('password_reset_token')
            self.password_reset_expires = data.get('password_reset_expires')
        else:
            self._id = None
            self.email = None
            self.password_hash = None
            self.full_name = None
            self.phone = ''
            self.role = self.ROLE_PORTAL_USER
            self.contact_id = None
            self.is_active = True
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            self.last_login = None
            self.password_reset_token = None
            self.password_reset_expires = None
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_password=False):
        data = {
            '_id': str(self._id) if self._id else None,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role,
            'contact_id': str(self.contact_id) if self.contact_id else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        if include_password:
            data['password_hash'] = self.password_hash
        return data
    
    def to_db_dict(self):
        data = {
            'email': self.email,
            'password_hash': self.password_hash,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role,
            'contact_id': ObjectId(self.contact_id) if self.contact_id else None,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_login': self.last_login,
            'password_reset_token': self.password_reset_token,
            'password_reset_expires': self.password_reset_expires
        }
        return data
    
    @staticmethod
    def from_db(data):
        if data:
            return User(data)
        return None
