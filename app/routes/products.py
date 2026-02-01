from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.product import Product
from app.utils.helpers import admin_required

products_bp = Blueprint('products', __name__)

@products_bp.route('', methods=['GET'])
@jwt_required()
def get_products():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    product_type = request.args.get('type', '')
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    
    query = {}
    
    if not include_archived:
        query['is_archived'] = False
    
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'sku': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
    
    if category:
        query['category'] = category
    
    if product_type:
        query['product_type'] = product_type
    
    total = db.products.count_documents(query)
    products = list(db.products.find(query).sort('name', 1).skip((page - 1) * per_page).limit(per_page))
    
    return jsonify({
        'products': [Product.from_db(p).to_dict() for p in products],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@products_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    db = get_db()
    
    categories = db.products.distinct('category', {'is_archived': False})
    categories = [c for c in categories if c]
    
    return jsonify({'categories': sorted(categories)}), 200

@products_bp.route('/<product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    db = get_db()
    
    product_data = db.products.find_one({'_id': ObjectId(product_id)})
    if not product_data:
        return jsonify({'error': 'Product not found'}), 404
    
    product = Product.from_db(product_data)
    response = product.to_dict()
    
    if product.default_analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(product.default_analytical_account_id)})
        if account:
            response['default_analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    return jsonify(response), 200

@products_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_product():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data.get('name') or not data.get('sku'):
        return jsonify({'error': 'Name and SKU are required'}), 400
    
    if data.get('product_type') and data['product_type'] not in Product.PRODUCT_TYPES:
        return jsonify({'error': f'Invalid product type. Must be one of: {Product.PRODUCT_TYPES}'}), 400
    
    db = get_db()
    
    if db.products.find_one({'sku': data['sku'].upper()}):
        return jsonify({'error': 'SKU already exists'}), 400
    
    product = Product()
    product.name = data['name']
    product.sku = data['sku'].upper()
    product.description = data.get('description')
    product.product_type = data.get('product_type', Product.TYPE_GOODS)
    product.category = data.get('category')
    product.unit = data.get('unit', 'pcs')
    product.purchase_price = float(data.get('purchase_price', 0))
    product.sale_price = float(data.get('sale_price', 0))
    product.tax_rate = float(data.get('tax_rate', 18))
    product.hsn_code = data.get('hsn_code')
    product.default_analytical_account_id = data.get('default_analytical_account_id')
    product.created_by = user_id
    product.created_at = datetime.utcnow()
    product.updated_at = datetime.utcnow()
    
    result = db.products.insert_one(product.to_db_dict())
    product._id = result.inserted_id
    
    return jsonify({
        'message': 'Product created successfully',
        'product': product.to_dict()
    }), 201

@products_bp.route('/<product_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_product(product_id):
    data = request.get_json()
    db = get_db()
    
    product_data = db.products.find_one({'_id': ObjectId(product_id)})
    if not product_data:
        return jsonify({'error': 'Product not found'}), 404
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'sku' in data and data['sku'].upper() != product_data['sku']:
        if db.products.find_one({'sku': data['sku'].upper(), '_id': {'$ne': ObjectId(product_id)}}):
            return jsonify({'error': 'SKU already exists'}), 400
        update_data['sku'] = data['sku'].upper()
    
    allowed_fields = ['name', 'description', 'product_type', 'category', 'unit',
                      'purchase_price', 'sale_price', 'tax_rate', 'hsn_code',
                      'default_analytical_account_id']
    
    for field in allowed_fields:
        if field in data:
            if field == 'product_type':
                if data[field] not in Product.PRODUCT_TYPES:
                    return jsonify({'error': f'Invalid product type. Must be one of: {Product.PRODUCT_TYPES}'}), 400
            if field in ['purchase_price', 'sale_price', 'tax_rate']:
                update_data[field] = float(data[field])
            elif field == 'default_analytical_account_id':
                update_data[field] = ObjectId(data[field]) if data[field] else None
            else:
                update_data[field] = data[field]
    
    db.products.update_one({'_id': ObjectId(product_id)}, {'$set': update_data})
    
    updated_product = db.products.find_one({'_id': ObjectId(product_id)})
    
    return jsonify({
        'message': 'Product updated successfully',
        'product': Product.from_db(updated_product).to_dict()
    }), 200

@products_bp.route('/<product_id>/archive', methods=['POST'])
@jwt_required()
@admin_required
def archive_product(product_id):
    db = get_db()
    
    product_data = db.products.find_one({'_id': ObjectId(product_id)})
    if not product_data:
        return jsonify({'error': 'Product not found'}), 404
    
    new_status = not product_data.get('is_archived', False)
    
    db.products.update_one(
        {'_id': ObjectId(product_id)},
        {'$set': {'is_archived': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"Product {'archived' if new_status else 'unarchived'} successfully",
        'is_archived': new_status
    }), 200

@products_bp.route('/<product_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_product(product_id):
    db = get_db()
    
    result = db.products.delete_one({'_id': ObjectId(product_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({'message': 'Product deleted successfully'}), 200
