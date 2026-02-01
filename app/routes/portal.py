from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
import os

from app.database import get_db
from app.models.user import User
from app.services.pdf_service import PDFService
from app.services.file_service import FileService
from app.services.razorpay_service import RazorpayService

portal_bp = Blueprint('portal', __name__)

def get_portal_user_contact(user_id):
    """Get user and their linked contact for portal users and vendors"""
    db = get_db()
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return None, None
    
    # Allow both portal_user (customer) and vendor roles
    if user.get('role') not in [User.ROLE_PORTAL_USER, User.ROLE_VENDOR]:
        return None, None
    
    contact_id = user.get('contact_id')
    if not contact_id:
        return None, None
    
    contact = db.contacts.find_one({'_id': ObjectId(contact_id)})
    return user, contact

@portal_bp.route('/invoices', methods=['GET'])
@jwt_required()
def get_my_invoices():
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        if user_data and user_data.get('role') == User.ROLE_ADMIN:
            return jsonify({'error': 'Use admin endpoints for full access'}), 400
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    payment_status = request.args.get('payment_status', '')
    
    # Query by contact_id - also check by contact email for matching
    contact_id = contact['_id']
    contact_email = contact.get('email', '').lower()
    
    # Build query to match by customer_id - include all statuses except cancelled
    query = {
        'customer_id': contact_id,
        'status': {'$in': ['draft', 'posted']}
    }
    
    if payment_status:
        query['payment_status'] = payment_status
    
    total = db.customer_invoices.count_documents(query)
    invoices = list(db.customer_invoices.find(query).sort('invoice_date', -1).skip((page - 1) * per_page).limit(per_page))
    
    invoice_list = []
    for inv in invoices:
        invoice_list.append({
            '_id': str(inv['_id']),
            'invoice_number': inv.get('invoice_number'),
            'invoice_date': inv.get('invoice_date').isoformat() if inv.get('invoice_date') else None,
            'due_date': inv.get('due_date').isoformat() if inv.get('due_date') else None,
            'total_amount': inv.get('total_amount'),
            'amount_paid': inv.get('amount_paid'),
            'amount_due': inv.get('amount_due'),
            'status': inv.get('status'),
            'payment_status': inv.get('payment_status'),
            'document_url': inv.get('document_url')
        })
    
    return jsonify({
        'invoices': invoice_list,
        'total': total,
        'page': page,
        'per_page': per_page
    }), 200

@portal_bp.route('/invoices/<invoice_id>', methods=['GET'])
@jwt_required()
def get_my_invoice(invoice_id):
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    invoice = db.customer_invoices.find_one({
        '_id': ObjectId(invoice_id),
        'customer_id': contact['_id'],
        'status': {'$in': ['draft', 'posted']}
    })
    
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    payments = list(db.payments.find({'invoice_id': ObjectId(invoice_id)}))
    
    return jsonify({
        '_id': str(invoice['_id']),
        'invoice_number': invoice.get('invoice_number'),
        'invoice_date': invoice.get('invoice_date').isoformat() if invoice.get('invoice_date') else None,
        'due_date': invoice.get('due_date').isoformat() if invoice.get('due_date') else None,
        'items': invoice.get('items', []),
        'subtotal': invoice.get('subtotal'),
        'tax_amount': invoice.get('tax_amount'),
        'discount_amount': invoice.get('discount_amount'),
        'total_amount': invoice.get('total_amount'),
        'amount_paid': invoice.get('amount_paid'),
        'amount_due': invoice.get('amount_due'),
        'payment_status': invoice.get('payment_status'),
        'document_url': invoice.get('document_url'),
        'payments': [{
            '_id': str(p['_id']),
            'payment_number': p.get('payment_number'),
            'amount': p.get('amount'),
            'payment_date': p.get('payment_date').isoformat() if p.get('payment_date') else None,
            'payment_method': p.get('payment_method')
        } for p in payments]
    }), 200

@portal_bp.route('/invoices/<invoice_id>/download', methods=['GET'])
@jwt_required()
def download_my_invoice(invoice_id):
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    # First check if invoice exists at all
    invoice = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Verify the invoice belongs to this customer (compare as strings to handle ObjectId vs string)
    invoice_customer_id = str(invoice.get('customer_id')) if invoice.get('customer_id') else None
    contact_id_str = str(contact['_id'])
    
    if invoice_customer_id != contact_id_str:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # If blob_name exists, generate fresh SAS URL
    if invoice.get('blob_name'):
        sas_url = FileService.get_file_url_with_sas(invoice['blob_name'])
        if sas_url:
            return jsonify({'url': sas_url}), 200
    
    # Try to extract blob_name from existing document_url
    if invoice.get('document_url'):
        try:
            url = invoice['document_url']
            # Extract blob path from URL like: https://account.blob.core.windows.net/files/invoices/2026/01/file.pdf
            if 'blob.core.windows.net' in url:
                # Split URL and find the container name (files)
                # URL format: https://account.blob.core.windows.net/files/invoices/2026/01/file.pdf
                url_without_query = url.split('?')[0]
                parts = url_without_query.split('/')
                # Find index of 'files' container
                if 'files' in parts:
                    container_idx = parts.index('files')
                    # blob_name is everything after the container
                    blob_name = '/'.join(parts[container_idx + 1:])
                    if blob_name:
                        sas_url = FileService.get_file_url_with_sas(blob_name)
                        if sas_url:
                            # Update the invoice with blob_name for future use
                            db.customer_invoices.update_one(
                                {'_id': ObjectId(invoice_id)},
                                {'$set': {'blob_name': blob_name}}
                            )
                            return jsonify({'url': sas_url}), 200
        except Exception as e:
            print(f"Error extracting blob_name: {e}")
    
    # Generate new PDF if no existing blob found
    invoice_dict = {
        'invoice_number': invoice.get('invoice_number'),
        'invoice_date': invoice.get('invoice_date').strftime('%Y-%m-%d') if invoice.get('invoice_date') else '',
        'due_date': invoice.get('due_date').strftime('%Y-%m-%d') if invoice.get('due_date') else '',
        'payment_status': invoice.get('payment_status'),
        'subtotal': invoice.get('subtotal'),
        'tax_amount': invoice.get('tax_amount'),
        'discount_amount': invoice.get('discount_amount'),
        'total_amount': invoice.get('total_amount'),
        'amount_paid': invoice.get('amount_paid'),
        'amount_due': invoice.get('amount_due')
    }
    
    pdf_content = PDFService.generate_invoice_pdf(invoice_dict, contact, invoice.get('items', []))
    
    result = FileService.upload_file_with_sas_url(
        pdf_content,
        f"Invoice_{invoice.get('invoice_number')}.pdf",
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

@portal_bp.route('/bills', methods=['GET'])
@jwt_required()
def get_my_bills():
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = {
        'vendor_id': contact['_id'],
        'status': 'posted'
    }
    
    total = db.vendor_bills.count_documents(query)
    bills = list(db.vendor_bills.find(query).sort('bill_date', -1).skip((page - 1) * per_page).limit(per_page))
    
    bill_list = []
    for bill in bills:
        bill_list.append({
            '_id': str(bill['_id']),
            'bill_number': bill.get('bill_number'),
            'bill_date': bill.get('bill_date').isoformat() if bill.get('bill_date') else None,
            'due_date': bill.get('due_date').isoformat() if bill.get('due_date') else None,
            'total_amount': bill.get('total_amount'),
            'amount_paid': bill.get('amount_paid'),
            'amount_due': bill.get('amount_due'),
            'payment_status': bill.get('payment_status'),
            'document_url': bill.get('document_url')
        })
    
    return jsonify({
        'bills': bill_list,
        'total': total,
        'page': page,
        'per_page': per_page
    }), 200

@portal_bp.route('/sales-orders', methods=['GET'])
@jwt_required()
def get_my_sales_orders():
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = {
        'customer_id': contact['_id'],
        'status': {'$ne': 'cancelled'}
    }
    
    total = db.sales_orders.count_documents(query)
    orders = list(db.sales_orders.find(query).sort('order_date', -1).skip((page - 1) * per_page).limit(per_page))
    
    order_list = []
    for order in orders:
        order_list.append({
            '_id': str(order['_id']),
            'so_number': order.get('so_number'),
            'order_date': order.get('order_date').isoformat() if order.get('order_date') else None,
            'delivery_date': order.get('delivery_date').isoformat() if order.get('delivery_date') else None,
            'status': order.get('status'),
            'total_amount': order.get('total_amount'),
            'document_url': order.get('document_url')
        })
    
    return jsonify({
        'sales_orders': order_list,
        'total': total,
        'page': page,
        'per_page': per_page
    }), 200

@portal_bp.route('/purchase-orders', methods=['GET'])
@jwt_required()
def get_my_purchase_orders():
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    query = {
        'vendor_id': contact['_id'],
        'status': {'$ne': 'cancelled'}
    }
    
    total = db.purchase_orders.count_documents(query)
    orders = list(db.purchase_orders.find(query).sort('order_date', -1).skip((page - 1) * per_page).limit(per_page))
    
    order_list = []
    for order in orders:
        order_list.append({
            '_id': str(order['_id']),
            'po_number': order.get('po_number'),
            'order_date': order.get('order_date').isoformat() if order.get('order_date') else None,
            'expected_date': order.get('expected_date').isoformat() if order.get('expected_date') else None,
            'status': order.get('status'),
            'total_amount': order.get('total_amount'),
            'document_url': order.get('document_url')
        })
    
    return jsonify({
        'purchase_orders': order_list,
        'total': total,
        'page': page,
        'per_page': per_page
    }), 200

@portal_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_my_profile():
    user_id = get_jwt_identity()
    db = get_db()
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    response = {
        '_id': str(user['_id']),
        'email': user.get('email'),
        'full_name': user.get('full_name'),
        'role': user.get('role')
    }
    
    if user.get('contact_id'):
        contact = db.contacts.find_one({'_id': user['contact_id']})
        if contact:
            response['contact'] = {
                '_id': str(contact['_id']),
                'name': contact.get('name'),
                'email': contact.get('email'),
                'phone': contact.get('phone'),
                'company_name': contact.get('company_name'),
                'billing_address': contact.get('billing_address'),
                'shipping_address': contact.get('shipping_address')
            }
    
    return jsonify(response), 200

@portal_bp.route('/bills/<bill_id>/download', methods=['GET'])
@jwt_required()
def download_my_bill(bill_id):
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    bill = db.vendor_bills.find_one({
        '_id': ObjectId(bill_id),
        'vendor_id': contact['_id'],
        'status': 'posted'
    })
    
    if not bill:
        return jsonify({'error': 'Bill not found'}), 404
    
    if bill.get('document_url'):
        return jsonify({'url': bill['document_url']}), 200
    
    return jsonify({'error': 'Document not available'}), 404

@portal_bp.route('/sales-orders/<order_id>/download', methods=['GET'])
@jwt_required()
def download_my_sales_order(order_id):
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    order = db.sales_orders.find_one({
        '_id': ObjectId(order_id),
        'customer_id': contact['_id']
    })
    
    if not order:
        return jsonify({'error': 'Sales order not found'}), 404
    
    # If document exists and has blob_name, generate fresh SAS URL
    if order.get('blob_name'):
        sas_url = FileService.get_file_url_with_sas(order['blob_name'])
        if sas_url:
            return jsonify({'url': sas_url}), 200
    
    # Generate PDF on-the-fly if not exists
    so_dict = {
        'so_number': order.get('so_number'),
        'order_date': order.get('order_date').strftime('%Y-%m-%d') if order.get('order_date') else '',
        'delivery_date': order.get('delivery_date').strftime('%Y-%m-%d') if order.get('delivery_date') else '',
        'status': order.get('status'),
        'subtotal': order.get('subtotal'),
        'tax_amount': order.get('tax_amount'),
        'discount_amount': order.get('discount_amount'),
        'total_amount': order.get('total_amount')
    }
    
    pdf_content = PDFService.generate_sales_order_pdf(so_dict, contact, order.get('items', []))
    
    result = FileService.upload_file_with_sas_url(
        pdf_content,
        f"SO_{order.get('so_number')}.pdf",
        'sales_orders',
        'application/pdf'
    )
    
    if result['success']:
        db.sales_orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': {'document_url': result['url'], 'blob_name': result['blob_name']}}
        )
        return jsonify({'url': result['url']}), 200
    
    return jsonify({'error': 'Failed to generate document'}), 500

@portal_bp.route('/purchase-orders/<order_id>/download', methods=['GET'])
@jwt_required()
def download_my_purchase_order(order_id):
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    order = db.purchase_orders.find_one({
        '_id': ObjectId(order_id),
        'vendor_id': contact['_id']
    })
    
    if not order:
        return jsonify({'error': 'Purchase order not found'}), 404
    
    if order.get('document_url'):
        return jsonify({'url': order['document_url']}), 200
    
    return jsonify({'error': 'Document not available'}), 404

@portal_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_my_profile():
    user_id = get_jwt_identity()
    db = get_db()
    data = request.get_json()
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    update_data = {}
    if data.get('full_name'):
        update_data['full_name'] = data['full_name']
    
    if update_data:
        update_data['updated_at'] = datetime.utcnow()
        db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
    
    if user.get('contact_id') and data.get('contact'):
        contact_update = {}
        contact_data = data['contact']
        
        if contact_data.get('phone'):
            contact_update['phone'] = contact_data['phone']
        if contact_data.get('billing_address'):
            contact_update['billing_address'] = contact_data['billing_address']
        if contact_data.get('shipping_address'):
            contact_update['shipping_address'] = contact_data['shipping_address']
        
        if contact_update:
            contact_update['updated_at'] = datetime.utcnow()
            db.contacts.update_one({'_id': user['contact_id']}, {'$set': contact_update})
    
    return jsonify({'message': 'Profile updated successfully'}), 200

@portal_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_my_summary():
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    pending_invoices = db.customer_invoices.count_documents({
        'customer_id': contact['_id'],
        'status': 'posted',
        'payment_status': {'$ne': 'paid'}
    })
    
    total_due_pipeline = [
        {'$match': {
            'customer_id': contact['_id'],
            'status': 'posted',
            'payment_status': {'$ne': 'paid'}
        }},
        {'$group': {'_id': None, 'total': {'$sum': '$amount_due'}}}
    ]
    total_due_result = list(db.customer_invoices.aggregate(total_due_pipeline))
    total_due = total_due_result[0]['total'] if total_due_result else 0
    
    active_orders = db.sales_orders.count_documents({
        'customer_id': contact['_id'],
        'status': {'$in': ['confirmed', 'draft']}
    })
    
    return jsonify({
        'pending_invoices': pending_invoices,
        'total_amount_due': total_due,
        'active_orders': active_orders
    }), 200

# Razorpay Payment Routes
@portal_bp.route('/payments/razorpay-key', methods=['GET'])
@jwt_required()
def get_razorpay_key():
    """Get Razorpay key ID for frontend"""
    key_id = RazorpayService.get_key_id()
    if not key_id:
        return jsonify({'error': 'Payment gateway not configured'}), 500
    return jsonify({'key_id': key_id}), 200

@portal_bp.route('/invoices/<invoice_id>/create-payment-order', methods=['POST'])
@jwt_required()
def create_invoice_payment_order(invoice_id):
    """Create a Razorpay order for invoice payment"""
    user_id = get_jwt_identity()
    db = get_db()
    
    user, contact = get_portal_user_contact(user_id)
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    # First find the invoice
    invoice = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Verify customer ownership (compare as strings)
    invoice_customer_id = str(invoice.get('customer_id')) if invoice.get('customer_id') else None
    contact_id_str = str(contact['_id'])
    
    if invoice_customer_id != contact_id_str:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Check if invoice is in valid status for payment
    if invoice.get('status') not in ['draft', 'posted']:
        return jsonify({'error': 'Invoice cannot be paid'}), 400
    
    if invoice.get('payment_status') == 'paid':
        return jsonify({'error': 'Invoice already paid'}), 400
    
    amount_due = invoice.get('amount_due', 0)
    if amount_due <= 0:
        return jsonify({'error': 'No amount due'}), 400
    
    try:
        order = RazorpayService.create_order(
            amount=amount_due,
            receipt=f"INV_{invoice.get('invoice_number')}",
            notes={
                'invoice_id': str(invoice['_id']),
                'invoice_number': invoice.get('invoice_number'),
                'customer_id': str(contact['_id'])
            }
        )
        
        return jsonify({
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'invoice_number': invoice.get('invoice_number'),
            'amount_due': amount_due
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@portal_bp.route('/invoices/<invoice_id>/verify-payment', methods=['POST'])
@jwt_required()
def verify_invoice_payment(invoice_id):
    """Verify and record Razorpay payment for invoice"""
    user_id = get_jwt_identity()
    db = get_db()
    data = request.get_json()
    
    user, contact = get_portal_user_contact(user_id)
    if not contact:
        return jsonify({'error': 'No contact linked to this account'}), 400
    
    # First find the invoice
    invoice = db.customer_invoices.find_one({'_id': ObjectId(invoice_id)})
    
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Verify customer ownership (compare as strings)
    invoice_customer_id = str(invoice.get('customer_id')) if invoice.get('customer_id') else None
    contact_id_str = str(contact['_id'])
    
    if invoice_customer_id != contact_id_str:
        return jsonify({'error': 'Invoice not found'}), 404
    
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({'error': 'Missing payment details'}), 400
    
    # Verify signature
    is_valid = RazorpayService.verify_payment(
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    )
    
    if not is_valid:
        return jsonify({'error': 'Payment verification failed'}), 400
    
    # Get payment details from Razorpay
    try:
        payment_details = RazorpayService.get_payment(razorpay_payment_id)
        amount_paid = payment_details['amount'] / 100  # Convert from paise
    except Exception as e:
        return jsonify({'error': f'Failed to fetch payment details: {str(e)}'}), 500
    
    # Generate payment number
    last_payment = db.payments.find_one(sort=[('created_at', -1)])
    payment_count = db.payments.count_documents({}) + 1
    payment_number = f"PAY-{datetime.utcnow().strftime('%Y%m')}-{payment_count:04d}"
    
    # Create payment record
    payment_data = {
        'payment_number': payment_number,
        'payment_type': 'incoming',
        'contact_id': contact['_id'],
        'invoice_id': ObjectId(invoice_id),
        'amount': amount_paid,
        'payment_date': datetime.utcnow(),
        'payment_method': 'razorpay',
        'reference_number': razorpay_payment_id,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'notes': f'Online payment for Invoice {invoice.get("invoice_number")}',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    
    db.payments.insert_one(payment_data)
    
    # Update invoice
    new_amount_paid = invoice.get('amount_paid', 0) + amount_paid
    new_amount_due = invoice.get('total_amount', 0) - new_amount_paid
    
    new_payment_status = 'paid' if new_amount_due <= 0 else 'partially_paid'
    
    db.customer_invoices.update_one(
        {'_id': ObjectId(invoice_id)},
        {'$set': {
            'amount_paid': new_amount_paid,
            'amount_due': max(0, new_amount_due),
            'payment_status': new_payment_status,
            'updated_at': datetime.utcnow()
        }}
    )
    
    return jsonify({
        'message': 'Payment successful',
        'payment_number': payment_number,
        'amount_paid': amount_paid,
        'new_amount_due': max(0, new_amount_due),
        'payment_status': new_payment_status
    }), 200
