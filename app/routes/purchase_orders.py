from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.purchase_order import PurchaseOrder
from app.utils.helpers import admin_required, generate_number, parse_date
from app.services.analytics_service import AnalyticsService
from app.services.pdf_service import PDFService
from app.services.file_service import FileService

purchase_orders_bp = Blueprint('purchase_orders', __name__)

@purchase_orders_bp.route('', methods=['GET'])
@jwt_required()
def get_purchase_orders():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    vendor_id = request.args.get('vendor_id', '')
    
    query = {}
    
    if search:
        query['$or'] = [
            {'po_number': {'$regex': search, '$options': 'i'}}
        ]
    
    if status:
        query['status'] = status
    
    if vendor_id:
        query['vendor_id'] = ObjectId(vendor_id)
    
    total = db.purchase_orders.count_documents(query)
    orders = list(db.purchase_orders.find(query).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    order_list = []
    for order_data in orders:
        order = PurchaseOrder.from_db(order_data)
        order_dict = order.to_dict()
        
        if order.vendor_id:
            vendor = db.contacts.find_one({'_id': ObjectId(order.vendor_id)})
            if vendor:
                order_dict['vendor'] = {
                    '_id': str(vendor['_id']),
                    'name': vendor.get('name'),
                    'company_name': vendor.get('company_name')
                }
        
        order_list.append(order_dict)
    
    return jsonify({
        'purchase_orders': order_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@purchase_orders_bp.route('/<po_id>', methods=['GET'])
@jwt_required()
def get_purchase_order(po_id):
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    order = PurchaseOrder.from_db(order_data)
    response = order.to_dict()
    
    if order.vendor_id:
        vendor = db.contacts.find_one({'_id': ObjectId(order.vendor_id)})
        if vendor:
            response['vendor'] = {
                '_id': str(vendor['_id']),
                'name': vendor.get('name'),
                'company_name': vendor.get('company_name'),
                'email': vendor.get('email'),
                'phone': vendor.get('phone')
            }
    
    if order.analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(order.analytical_account_id)})
        if account:
            response['analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    for item in response.get('items', []):
        if item.get('product_id'):
            product = db.products.find_one({'_id': ObjectId(item['product_id'])})
            if product:
                item['product'] = {
                    '_id': str(product['_id']),
                    'name': product.get('name'),
                    'sku': product.get('sku')
                }
    
    bills = list(db.vendor_bills.find({'purchase_order_id': ObjectId(po_id)}))
    response['bills'] = [{
        '_id': str(b['_id']),
        'bill_number': b.get('bill_number'),
        'total_amount': b.get('total_amount'),
        'payment_status': b.get('payment_status')
    } for b in bills]
    
    return jsonify(response), 200

@purchase_orders_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_purchase_order():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data.get('vendor_id'):
        return jsonify({'error': 'Vendor is required'}), 400
    
    if not data.get('items') or len(data['items']) == 0:
        return jsonify({'error': 'At least one item is required'}), 400
    
    db = get_db()
    
    vendor = db.contacts.find_one({'_id': ObjectId(data['vendor_id'])})
    if not vendor:
        return jsonify({'error': 'Vendor not found'}), 404
    
    order = PurchaseOrder()
    order.po_number = generate_number('PO', 'purchase_orders')
    order.vendor_id = data['vendor_id']
    order.order_date = parse_date(data.get('order_date')) or datetime.utcnow()
    order.expected_date = parse_date(data.get('expected_date'))
    order.status = PurchaseOrder.STATUS_DRAFT
    order.notes = data.get('notes')
    order.created_by = user_id
    order.created_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    
    items = []
    for item_data in data['items']:
        product = db.products.find_one({'_id': ObjectId(item_data['product_id'])})
        if not product:
            return jsonify({'error': f"Product {item_data['product_id']} not found"}), 404
        
        quantity = float(item_data.get('quantity', 1))
        unit_price = float(item_data.get('unit_price', product.get('purchase_price', 0)))
        tax_rate = float(item_data.get('tax_rate', product.get('tax_rate', 18)))
        subtotal = quantity * unit_price
        tax_amount = subtotal * (tax_rate / 100)
        
        item = {
            'product_id': str(product['_id']),
            'product_name': product.get('name'),
            'product_sku': product.get('sku'),
            'quantity': quantity,
            'unit': item_data.get('unit', product.get('unit', 'pcs')),
            'unit_price': unit_price,
            'tax_rate': tax_rate,
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'total': subtotal + tax_amount
        }
        items.append(item)
    
    order.items = items
    order.calculate_totals()
    
    analytical_account_id = data.get('analytical_account_id')
    if not analytical_account_id and items:
        first_product = db.products.find_one({'_id': ObjectId(items[0]['product_id'])})
        if first_product:
            analytical_account_id = AnalyticsService.get_analytical_account_for_transaction(
                product_id=first_product['_id'],
                category=first_product.get('category'),
                contact_id=data['vendor_id'],
                amount=order.total_amount
            )
    
    if analytical_account_id:
        order.analytical_account_id = str(analytical_account_id)
    
    result = db.purchase_orders.insert_one(order.to_db_dict())
    order._id = result.inserted_id
    
    return jsonify({
        'message': 'Purchase order created successfully',
        'purchase_order': order.to_dict()
    }), 201

@purchase_orders_bp.route('/<po_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_purchase_order(po_id):
    data = request.get_json()
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if order_data.get('status') not in [PurchaseOrder.STATUS_DRAFT]:
        return jsonify({'error': 'Only draft orders can be modified'}), 400
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'vendor_id' in data:
        vendor = db.contacts.find_one({'_id': ObjectId(data['vendor_id'])})
        if not vendor:
            return jsonify({'error': 'Vendor not found'}), 404
        update_data['vendor_id'] = ObjectId(data['vendor_id'])
    
    if 'order_date' in data:
        update_data['order_date'] = parse_date(data['order_date'])
    
    if 'expected_date' in data:
        update_data['expected_date'] = parse_date(data['expected_date'])
    
    if 'notes' in data:
        update_data['notes'] = data['notes']
    
    if 'analytical_account_id' in data:
        update_data['analytical_account_id'] = ObjectId(data['analytical_account_id']) if data['analytical_account_id'] else None
    
    if 'items' in data:
        items = []
        subtotal = 0
        tax_amount = 0
        
        for item_data in data['items']:
            product = db.products.find_one({'_id': ObjectId(item_data['product_id'])})
            if not product:
                return jsonify({'error': f"Product {item_data['product_id']} not found"}), 404
            
            quantity = float(item_data.get('quantity', 1))
            unit_price = float(item_data.get('unit_price', product.get('purchase_price', 0)))
            tax_rate = float(item_data.get('tax_rate', product.get('tax_rate', 18)))
            item_subtotal = quantity * unit_price
            item_tax = item_subtotal * (tax_rate / 100)
            
            item = {
                'product_id': str(product['_id']),
                'product_name': product.get('name'),
                'product_sku': product.get('sku'),
                'quantity': quantity,
                'unit': item_data.get('unit', product.get('unit', 'pcs')),
                'unit_price': unit_price,
                'tax_rate': tax_rate,
                'subtotal': item_subtotal,
                'tax_amount': item_tax,
                'total': item_subtotal + item_tax
            }
            items.append(item)
            subtotal += item_subtotal
            tax_amount += item_tax
        
        update_data['items'] = items
        update_data['subtotal'] = subtotal
        update_data['tax_amount'] = tax_amount
        update_data['total_amount'] = subtotal + tax_amount
    
    db.purchase_orders.update_one({'_id': ObjectId(po_id)}, {'$set': update_data})
    
    updated_order = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    
    return jsonify({
        'message': 'Purchase order updated successfully',
        'purchase_order': PurchaseOrder.from_db(updated_order).to_dict()
    }), 200

@purchase_orders_bp.route('/<po_id>/confirm', methods=['POST'])
@jwt_required()
@admin_required
def confirm_purchase_order(po_id):
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if order_data.get('status') != PurchaseOrder.STATUS_DRAFT:
        return jsonify({'error': 'Only draft orders can be confirmed'}), 400
    
    db.purchase_orders.update_one(
        {'_id': ObjectId(po_id)},
        {'$set': {'status': PurchaseOrder.STATUS_CONFIRMED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Purchase order confirmed successfully'}), 200

@purchase_orders_bp.route('/<po_id>/receive', methods=['POST'])
@jwt_required()
@admin_required
def receive_purchase_order(po_id):
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if order_data.get('status') != PurchaseOrder.STATUS_CONFIRMED:
        return jsonify({'error': 'Only confirmed orders can be marked as received'}), 400
    
    db.purchase_orders.update_one(
        {'_id': ObjectId(po_id)},
        {'$set': {'status': PurchaseOrder.STATUS_RECEIVED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Purchase order marked as received'}), 200

@purchase_orders_bp.route('/<po_id>/cancel', methods=['POST'])
@jwt_required()
@admin_required
def cancel_purchase_order(po_id):
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if order_data.get('status') == PurchaseOrder.STATUS_CANCELLED:
        return jsonify({'error': 'Order is already cancelled'}), 400
    
    has_bills = db.vendor_bills.find_one({'purchase_order_id': ObjectId(po_id)})
    if has_bills:
        return jsonify({'error': 'Cannot cancel order with associated bills'}), 400
    
    db.purchase_orders.update_one(
        {'_id': ObjectId(po_id)},
        {'$set': {'status': PurchaseOrder.STATUS_CANCELLED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Purchase order cancelled successfully'}), 200

@purchase_orders_bp.route('/<po_id>/pdf', methods=['GET'])
@jwt_required()
def generate_po_pdf(po_id):
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    order = PurchaseOrder.from_db(order_data)
    
    vendor = db.contacts.find_one({'_id': ObjectId(order.vendor_id)}) if order.vendor_id else {}
    
    po_dict = order.to_dict()
    po_dict['order_date'] = order.order_date.strftime('%Y-%m-%d') if order.order_date else ''
    po_dict['expected_date'] = order.expected_date.strftime('%Y-%m-%d') if order.expected_date else ''
    
    pdf_content = PDFService.generate_purchase_order_pdf(po_dict, vendor, order.items)
    
    result = FileService.upload_file_with_sas_url(
        pdf_content,
        f"PO_{order.po_number}.pdf",
        'purchase_orders',
        'application/pdf'
    )
    
    if result['success']:
        db.purchase_orders.update_one(
            {'_id': ObjectId(po_id)},
            {'$set': {'document_url': result['url'], 'blob_name': result['blob_name']}}
        )
        return jsonify({'url': result['url']}), 200
    else:
        return jsonify({'error': 'Failed to generate PDF'}), 500

@purchase_orders_bp.route('/<po_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_purchase_order(po_id):
    db = get_db()
    
    order_data = db.purchase_orders.find_one({'_id': ObjectId(po_id)})
    if not order_data:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if order_data.get('status') != PurchaseOrder.STATUS_DRAFT:
        return jsonify({'error': 'Only draft orders can be deleted'}), 400
    
    has_bills = db.vendor_bills.find_one({'purchase_order_id': ObjectId(po_id)})
    if has_bills:
        return jsonify({'error': 'Cannot delete order with associated bills'}), 400
    
    db.purchase_orders.delete_one({'_id': ObjectId(po_id)})
    
    return jsonify({'message': 'Purchase order deleted successfully'}), 200
