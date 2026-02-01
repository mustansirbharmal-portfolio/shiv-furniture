from datetime import datetime
from bson import ObjectId

class Product:
    TYPE_GOODS = 'goods'
    TYPE_SERVICE = 'service'
    
    PRODUCT_TYPES = [TYPE_GOODS, TYPE_SERVICE]
    
    def __init__(self, data=None):
        if data:
            self._id = data.get('_id')
            self.name = data.get('name')
            self.sku = data.get('sku')
            self.description = data.get('description')
            self.product_type = data.get('product_type', self.TYPE_GOODS)
            self.category = data.get('category')
            self.unit = data.get('unit', 'pcs')
            self.purchase_price = data.get('purchase_price', 0)
            self.sale_price = data.get('sale_price', 0)
            self.tax_rate = data.get('tax_rate', 18)
            self.hsn_code = data.get('hsn_code')
            self.default_analytical_account_id = data.get('default_analytical_account_id')
            self.is_archived = data.get('is_archived', False)
            self.created_by = data.get('created_by')
            self.created_at = data.get('created_at', datetime.utcnow())
            self.updated_at = data.get('updated_at', datetime.utcnow())
        else:
            self._id = None
            self.name = None
            self.sku = None
            self.description = None
            self.product_type = self.TYPE_GOODS
            self.category = None
            self.unit = 'pcs'
            self.purchase_price = 0
            self.sale_price = 0
            self.tax_rate = 18
            self.hsn_code = None
            self.default_analytical_account_id = None
            self.is_archived = False
            self.created_by = None
            self.created_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            '_id': str(self._id) if self._id else None,
            'name': self.name,
            'sku': self.sku,
            'description': self.description,
            'product_type': self.product_type,
            'category': self.category,
            'unit': self.unit,
            'purchase_price': self.purchase_price,
            'sale_price': self.sale_price,
            'tax_rate': self.tax_rate,
            'hsn_code': self.hsn_code,
            'default_analytical_account_id': str(self.default_analytical_account_id) if self.default_analytical_account_id else None,
            'is_archived': self.is_archived,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_db_dict(self):
        return {
            'name': self.name,
            'sku': self.sku,
            'description': self.description,
            'product_type': self.product_type,
            'category': self.category,
            'unit': self.unit,
            'purchase_price': self.purchase_price,
            'sale_price': self.sale_price,
            'tax_rate': self.tax_rate,
            'hsn_code': self.hsn_code,
            'default_analytical_account_id': ObjectId(self.default_analytical_account_id) if self.default_analytical_account_id else None,
            'is_archived': self.is_archived,
            'created_by': ObjectId(self.created_by) if self.created_by else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def from_db(data):
        if data:
            return Product(data)
        return None
