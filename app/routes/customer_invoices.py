from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from bson import ObjectId

from app.database import get_db
from app.models.customer_invoice import CustomerInvoice
from app.utils.helpers import admin_required, generate_number, parse_date
from app.services.analytics_service import AnalyticsService
from app.services.pdf_service import PDFService
from app.services.file_service import FileService
from app.services.email_service import EmailService

customer_invoices_bp = Blueprint('customer_invoices', __name__)

@customer_invoices_bp.route('', methods=['GET'])
@jwt_required()
def get_customer_invoices():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    payment_status = request.args.get('payment_status', '')
    customer_id = request.args.get('customer_id', '')
    
    query = {}
    
    if search:
        query['invoice_number'] = {'$regex': search, '$options': 'i'}
    
    if status:
        query['status'] = status
    
    if payment_status:
        query['payment_status'] = payment_status
    
    if customer_id:
        query['customer_id'] = ObjectId(customer_id)
    
    total = db.customer_invoices.count_documents(query)
    invoices = list(db.customer_invoices.find(query).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    invoice_list = []
    for invoice_data in invoices:
        invoice = CustomerInvoice.from_db(invoice_data)
        invoice_dict = invoice.to_dict()
        
        if invoice.customer_id:
            customer = db.contacts.find_one({'_id': ObjectId(invoice.customer_id)})
            if customer:
                invoice_dict['customer'] = {
                    '_id': str(customer['_id']),
                    'name': customer.get('name'),
                    'company_name': customer.get('company_name')
                }
        
        invoice_list.append(invoice_dict)
    
    return jsonify({
        'customer_invoices': invoice_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@customer_invoices_bp.route('/<invoice_id>', methods=['GET'])
@jwt_required()
def get_customer_invoice(invoice_id):
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    invoice = CustomerInvoice.from_db(invoice_data)
    response = invoice.to_dict()
    
    if invoice.customer_id:
        customer = db.contacts.find_one({'_id': ObjectId(invoice.customer_id)})
        if customer:
            response['customer'] = {
                '_id': str(customer['_id']),
                'name': customer.get('name'),
                'company_name': customer.get('company_name'),
                'email': customer.get('email'),
                'phone': customer.get('phone'),
                'billing_address': customer.get('billing_address', {})
            }
    
    if invoice.sales_order_id:
        so = db.sales_orders.find_one({'_id': ObjectId(invoice.sales_order_id)})
        if so:
            response['sales_order'] = {
                '_id': str(so['_id']),
                'so_number': so.get('so_number')
            }
    
    if invoice.analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(invoice.analytical_account_id)})
        if account:
            response['analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    payments = list(db.payments.find({'invoice_id': ObjectId(invoice_id)}))
    response['payments'] = [{
        '_id': str(p['_id']),
        'payment_number': p.get('payment_number'),
        'amount': p.get('amount'),
        'payment_date': p.get('payment_date').isoformat() if p.get('payment_date') else None,
        'payment_method': p.get('payment_method')
    } for p in payments]
    
    return jsonify(response), 200

@customer_invoices_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_customer_invoice():
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
    
    invoice = CustomerInvoice()
    invoice.invoice_number = generate_number('INV', 'customer_invoices')
    invoice.customer_id = data['customer_id']
    invoice.sales_order_id = data.get('sales_order_id')
    invoice.invoice_date = parse_date(data.get('invoice_date')) or datetime.utcnow()
    invoice.due_date = parse_date(data.get('due_date')) or (invoice.invoice_date + timedelta(days=customer.get('payment_terms', 30)))
    invoice.status = CustomerInvoice.STATUS_DRAFT
    invoice.payment_status = CustomerInvoice.PAYMENT_STATUS_NOT_PAID
    invoice.discount_amount = float(data.get('discount_amount', 0))
    invoice.notes = data.get('notes')
    invoice.created_by = user_id
    invoice.created_at = datetime.utcnow()
    invoice.updated_at = datetime.utcnow()
    
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
    
    invoice.items = items
    invoice.calculate_totals()
    
    analytical_account_id = data.get('analytical_account_id')
    if not analytical_account_id and items:
        first_product = db.products.find_one({'_id': ObjectId(items[0]['product_id'])})
        if first_product:
            analytical_account_id = AnalyticsService.get_analytical_account_for_transaction(
                product_id=first_product['_id'],
                category=first_product.get('category'),
                contact_id=data['customer_id'],
                amount=invoice.total_amount
            )
    
    if analytical_account_id:
        invoice.analytical_account_id = str(analytical_account_id)
    
    result = db.customer_invoices.insert_one(invoice.to_db_dict())
    invoice._id = result.inserted_id
    
    return jsonify({
        'message': 'Invoice created successfully',
        'customer_invoice': invoice.to_dict()
    }), 201

@customer_invoices_bp.route('/<invoice_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_customer_invoice(invoice_id):
    data = request.get_json()
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    if invoice_data.get('status') != CustomerInvoice.STATUS_DRAFT:
        return jsonify({'error': 'Only draft invoices can be modified'}), 400
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'customer_id' in data:
        customer = db.contacts.find_one({'_id': ObjectId(data['customer_id'])})
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        update_data['customer_id'] = ObjectId(data['customer_id'])
    
    if 'invoice_date' in data:
        update_data['invoice_date'] = parse_date(data['invoice_date'])
    
    if 'due_date' in data:
        update_data['due_date'] = parse_date(data['due_date'])
    
    if 'discount_amount' in data:
        update_data['discount_amount'] = float(data['discount_amount'])
    
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
        
        discount = update_data.get('discount_amount', invoice_data.get('discount_amount', 0))
        total = subtotal + tax_amount - discount
        update_data['items'] = items
        update_data['subtotal'] = subtotal
        update_data['tax_amount'] = tax_amount
        update_data['total_amount'] = total
        update_data['amount_due'] = total - invoice_data.get('amount_paid', 0)
    
    db.customer_invoices.update_one({'_id': ObjectId(invoice_id)}, {'$set': update_data})
    
    updated_invoice = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    
    return jsonify({
        'message': 'Invoice updated successfully',
        'customer_invoice': CustomerInvoice.from_db(updated_invoice).to_dict()
    }), 200

@customer_invoices_bp.route('/<invoice_id>/post', methods=['POST'])
@jwt_required()
@admin_required
def post_customer_invoice(invoice_id):
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    if invoice_data.get('status') != CustomerInvoice.STATUS_DRAFT:
        return jsonify({'error': 'Only draft invoices can be posted'}), 400
    
    db.customer_invoices.update_one(
        {'_id': ObjectId(invoice_id)},
        {'$set': {'status': CustomerInvoice.STATUS_POSTED, 'updated_at': datetime.utcnow()}}
    )
    
    customer = db.contacts.find_one({'_id': invoice_data.get('customer_id')})
    if customer and customer.get('email'):
        due_date = invoice_data.get('due_date')
        due_date_str = due_date.strftime('%Y-%m-%d') if due_date else 'N/A'
        EmailService.send_invoice_email(
            customer.get('email'),
            customer.get('name'),
            invoice_data.get('invoice_number'),
            invoice_data.get('total_amount', 0),
            due_date_str
        )
    
    return jsonify({'message': 'Invoice posted successfully'}), 200

@customer_invoices_bp.route('/<invoice_id>/cancel', methods=['POST'])
@jwt_required()
@admin_required
def cancel_customer_invoice(invoice_id):
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    if invoice_data.get('status') == CustomerInvoice.STATUS_CANCELLED:
        return jsonify({'error': 'Invoice is already cancelled'}), 400
    
    if invoice_data.get('amount_paid', 0) > 0:
        return jsonify({'error': 'Cannot cancel invoice with payments'}), 400
    
    db.customer_invoices.update_one(
        {'_id': ObjectId(invoice_id)},
        {'$set': {'status': CustomerInvoice.STATUS_CANCELLED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Invoice cancelled successfully'}), 200

@customer_invoices_bp.route('/<invoice_id>/pdf', methods=['GET'])
@jwt_required()
def generate_invoice_pdf(invoice_id):
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    invoice = CustomerInvoice.from_db(invoice_data)
    customer = db.contacts.find_one({'_id': ObjectId(invoice.customer_id)}) if invoice.customer_id else {}
    
    invoice_dict = invoice.to_dict()
    invoice_dict['invoice_date'] = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else ''
    invoice_dict['due_date'] = invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else ''
    
    pdf_content = PDFService.generate_invoice_pdf(invoice_dict, customer, invoice.items)
    
    result = FileService.upload_file_with_sas_url(
        pdf_content,
        f"Invoice_{invoice.invoice_number}.pdf",
        'invoices',
        'application/pdf'
    )
    
    if result['success']:
        db.customer_invoices.update_one(
            {'_id': ObjectId(invoice_id)},
            {'$set': {'document_url': result['url'], 'blob_name': result['blob_name']}}
        )
        return jsonify({'url': result['url']}), 200
    else:
        return jsonify({'error': 'Failed to generate PDF'}), 500

@customer_invoices_bp.route('/<invoice_id>/send-email', methods=['POST'])
@jwt_required()
@admin_required
def send_invoice_email(invoice_id):
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    customer = db.contacts.find_one({'_id': invoice_data.get('customer_id')})
    if not customer or not customer.get('email'):
        return jsonify({'error': 'Customer email not found'}), 400
    
    due_date = invoice_data.get('due_date')
    due_date_str = due_date.strftime('%Y-%m-%d') if due_date else 'N/A'
    
    success = EmailService.send_invoice_email(
        customer.get('email'),
        customer.get('name'),
        invoice_data.get('invoice_number'),
        invoice_data.get('total_amount', 0),
        due_date_str
    )
    
    if success:
        return jsonify({'message': 'Invoice email sent successfully'}), 200
    else:
        return jsonify({'error': 'Failed to send email'}), 500

@customer_invoices_bp.route('/<invoice_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_customer_invoice(invoice_id):
    db = get_db()
    
    invoice_data = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    if not invoice_data:
        return jsonify({'error': 'Invoice not found'}), 404
    
    if invoice_data.get('status') != CustomerInvoice.STATUS_DRAFT:
        return jsonify({'error': 'Only draft invoices can be deleted'}), 400
    
    db.customer_invoices.delete_one({'_id': ObjectId(invoice_id)})
    
    return jsonify({'message': 'Invoice deleted successfully'}), 200
