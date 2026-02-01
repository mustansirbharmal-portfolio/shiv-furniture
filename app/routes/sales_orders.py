from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.sales_order import SalesOrder
from app.utils.helpers import admin_required, generate_number, parse_date
from app.services.analytics_service import AnalyticsService
from app.services.pdf_service import PDFService
from app.services.file_service import FileService

sales_orders_bp = Blueprint('sales_orders', __name__)

@sales_orders_bp.route('', methods=['GET'])
@jwt_required()
def get_sales_orders():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    customer_id = request.args.get('customer_id', '')
    
    query = {}
    
    if search:
        query['so_number'] = {'$regex': search, '$options': 'i'}
    
    if status:
        query['status'] = status
    
    if customer_id:
        query['customer_id'] = ObjectId(customer_id)
    
    total = db.sales_orders.count_documents(query)
    orders = list(db.sales_orders.find(query).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    order_list = []
    for order_data in orders:
        order = SalesOrder.from_db(order_data)
        order_dict = order.to_dict()
        
        if order.customer_id:
            customer = db.contacts.find_one({'_id': ObjectId(order.customer_id)})
            if customer:
                order_dict['customer'] = {
                    '_id': str(customer['_id']),
                    'name': customer.get('name'),
                    'company_name': customer.get('company_name')
                }
        
        order_list.append(order_dict)
    
    return jsonify({
        'sales_orders': order_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@sales_orders_bp.route('/<so_id>', methods=['GET'])
@jwt_required()
def get_sales_order(so_id):
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    order = SalesOrder.from_db(order_data)
    response = order.to_dict()
    
    if order.customer_id:
        customer = db.contacts.find_one({'_id': ObjectId(order.customer_id)})
        if customer:
            response['customer'] = {
                '_id': str(customer['_id']),
                'name': customer.get('name'),
                'company_name': customer.get('company_name'),
                'email': customer.get('email'),
                'phone': customer.get('phone')
            }
    
    if order.analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(order.analytical_account_id)})
        if account:
            response['analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    invoices = list(db.customer_invoices.find({'sales_order_id': ObjectId(so_id)}))
    response['invoices'] = [{
        '_id': str(inv['_id']),
        'invoice_number': inv.get('invoice_number'),
        'total_amount': inv.get('total_amount'),
        'payment_status': inv.get('payment_status')
    } for inv in invoices]
    
    return jsonify(response), 200

@sales_orders_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_sales_order():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data.get('customer_id'):
        return jsonify({'error': 'Customer is required'}), 400
    
    if not data.get('items') or len(data['items']) == 0:
        return jsonify({'error': 'At least one item is required'}), 400
    
    db = get_db()
    
    customer = db.contacts.find_one({'_id': ObjectId(data['customer_id'])})
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    order = SalesOrder()
    order.so_number = generate_number('SO', 'sales_orders')
    order.customer_id = data['customer_id']
    order.order_date = parse_date(data.get('order_date')) or datetime.utcnow()
    order.delivery_date = parse_date(data.get('delivery_date'))
    order.status = SalesOrder.STATUS_DRAFT
    order.discount_amount = float(data.get('discount_amount', 0))
    order.shipping_address = data.get('shipping_address', customer.get('shipping_address', {}))
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
        unit_price = float(item_data.get('unit_price', product.get('sale_price', 0)))
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
                contact_id=data['customer_id'],
                amount=order.total_amount
            )
    
    if analytical_account_id:
        order.analytical_account_id = str(analytical_account_id)
    
    result = db.sales_orders.insert_one(order.to_db_dict())
    order._id = result.inserted_id
    
    return jsonify({
        'message': 'Sales order created successfully',
        'sales_order': order.to_dict()
    }), 201

@sales_orders_bp.route('/<so_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_sales_order(so_id):
    data = request.get_json()
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    if order_data.get('status') not in [SalesOrder.STATUS_DRAFT]:
        return jsonify({'error': 'Only draft orders can be modified'}), 400
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'customer_id' in data:
        customer = db.contacts.find_one({'_id': ObjectId(data['customer_id'])})
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        update_data['customer_id'] = ObjectId(data['customer_id'])
    
    if 'order_date' in data:
        update_data['order_date'] = parse_date(data['order_date'])
    
    if 'delivery_date' in data:
        update_data['delivery_date'] = parse_date(data['delivery_date'])
    
    if 'discount_amount' in data:
        update_data['discount_amount'] = float(data['discount_amount'])
    
    if 'shipping_address' in data:
        update_data['shipping_address'] = data['shipping_address']
    
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
            unit_price = float(item_data.get('unit_price', product.get('sale_price', 0)))
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
        
        discount = update_data.get('discount_amount', order_data.get('discount_amount', 0))
        update_data['items'] = items
        update_data['subtotal'] = subtotal
        update_data['tax_amount'] = tax_amount
        update_data['total_amount'] = subtotal + tax_amount - discount
    
    db.sales_orders.update_one({'_id': ObjectId(so_id)}, {'$set': update_data})
    
    updated_order = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    
    return jsonify({
        'message': 'Sales order updated successfully',
        'sales_order': SalesOrder.from_db(updated_order).to_dict()
    }), 200

@sales_orders_bp.route('/<so_id>/confirm', methods=['POST'])
@jwt_required()
@admin_required
def confirm_sales_order(so_id):
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    if order_data.get('status') != SalesOrder.STATUS_DRAFT:
        return jsonify({'error': 'Only draft orders can be confirmed'}), 400
    
    db.sales_orders.update_one(
        {'_id': ObjectId(so_id)},
        {'$set': {'status': SalesOrder.STATUS_CONFIRMED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Sales order confirmed successfully'}), 200

@sales_orders_bp.route('/<so_id>/deliver', methods=['POST'])
@jwt_required()
@admin_required
def deliver_sales_order(so_id):
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    if order_data.get('status') != SalesOrder.STATUS_CONFIRMED:
        return jsonify({'error': 'Only confirmed orders can be marked as delivered'}), 400
    
    db.sales_orders.update_one(
        {'_id': ObjectId(so_id)},
        {'$set': {'status': SalesOrder.STATUS_DELIVERED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Sales order marked as delivered'}), 200

@sales_orders_bp.route('/<so_id>/cancel', methods=['POST'])
@jwt_required()
@admin_required
def cancel_sales_order(so_id):
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    if order_data.get('status') == SalesOrder.STATUS_CANCELLED:
        return jsonify({'error': 'Order is already cancelled'}), 400
    
    has_invoices = db.customer_invoices.find_one({'sales_order_id': ObjectId(so_id)})
    if has_invoices:
        return jsonify({'error': 'Cannot cancel order with associated invoices'}), 400
    
    db.sales_orders.update_one(
        {'_id': ObjectId(so_id)},
        {'$set': {'status': SalesOrder.STATUS_CANCELLED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Sales order cancelled successfully'}), 200

@sales_orders_bp.route('/<so_id>/pdf', methods=['GET'])
@jwt_required()
def generate_so_pdf(so_id):
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    order = SalesOrder.from_db(order_data)
    customer = db.contacts.find_one({'_id': ObjectId(order.customer_id)}) if order.customer_id else {}
    
    so_dict = order.to_dict()
    so_dict['order_date'] = order.order_date.strftime('%Y-%m-%d') if order.order_date else ''
    so_dict['delivery_date'] = order.delivery_date.strftime('%Y-%m-%d') if order.delivery_date else ''
    
    pdf_content = PDFService.generate_sales_order_pdf(so_dict, customer, order.items)
    
    result = FileService.upload_file_with_sas_url(
        pdf_content,
        f"SO_{order.so_number}.pdf",
        'sales_orders',
        'application/pdf'
    )
    
    if result['success']:
        db.sales_orders.update_one(
            {'_id': ObjectId(so_id)},
            {'$set': {'document_url': result['url'], 'blob_name': result['blob_name']}}
        )
        return jsonify({'url': result['url']}), 200
    else:
        return jsonify({'error': 'Failed to generate PDF'}), 500

@sales_orders_bp.route('/<so_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_sales_order(so_id):
    db = get_db()
    
    order_data = db.sales_orders.find_one({'_id': ObjectId(so_id)})
    if not order_data:
        return jsonify({'error': 'Sales order not found'}), 404
    
    if order_data.get('status') != SalesOrder.STATUS_DRAFT:
        return jsonify({'error': 'Only draft orders can be deleted'}), 400
    
    has_invoices = db.customer_invoices.find_one({'sales_order_id': ObjectId(so_id)})
    if has_invoices:
        return jsonify({'error': 'Cannot delete order with associated invoices'}), 400
    
    db.sales_orders.delete_one({'_id': ObjectId(so_id)})
    
    return jsonify({'message': 'Sales order deleted successfully'}), 200
