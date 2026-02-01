from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.payment import Payment
from app.utils.helpers import admin_required, generate_number, parse_date
from app.services.email_service import EmailService

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('', methods=['GET'])
@jwt_required()
def get_payments():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    payment_type = request.args.get('type', '')
    contact_id = request.args.get('contact_id', '')
    
    query = {}
    
    if search:
        query['$or'] = [
            {'payment_number': {'$regex': search, '$options': 'i'}},
            {'reference_number': {'$regex': search, '$options': 'i'}}
        ]
    
    if payment_type:
        query['payment_type'] = payment_type
    
    if contact_id:
        query['contact_id'] = ObjectId(contact_id)
    
    total = db.payments.count_documents(query)
    payments = list(db.payments.find(query).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    payment_list = []
    for payment_data in payments:
        payment = Payment.from_db(payment_data)
        payment_dict = payment.to_dict()
        
        if payment.contact_id:
            contact = db.contacts.find_one({'_id': ObjectId(payment.contact_id)})
            if contact:
                payment_dict['contact'] = {
                    '_id': str(contact['_id']),
                    'name': contact.get('name'),
                    'company_name': contact.get('company_name')
                }
        
        if payment.invoice_id:
            invoice = db.customer_invoices.find_one({'_id': ObjectId(payment.invoice_id)})
            if invoice:
                payment_dict['invoice'] = {
                    '_id': str(invoice['_id']),
                    'invoice_number': invoice.get('invoice_number')
                }
        
        if payment.bill_id:
            bill = db.vendor_bills.find_one({'_id': ObjectId(payment.bill_id)})
            if bill:
                payment_dict['bill'] = {
                    '_id': str(bill['_id']),
                    'bill_number': bill.get('bill_number')
                }
        
        payment_list.append(payment_dict)
    
    return jsonify({
        'payments': payment_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@payments_bp.route('/<payment_id>', methods=['GET'])
@jwt_required()
def get_payment(payment_id):
    db = get_db()
    
    payment_data = db.payments.find_one({'_id': ObjectId(payment_id)})
    if not payment_data:
        return jsonify({'error': 'Payment not found'}), 404
    
    payment = Payment.from_db(payment_data)
    response = payment.to_dict()
    
    if payment.contact_id:
        contact = db.contacts.find_one({'_id': ObjectId(payment.contact_id)})
        if contact:
            response['contact'] = {
                '_id': str(contact['_id']),
                'name': contact.get('name'),
                'company_name': contact.get('company_name'),
                'email': contact.get('email')
            }
    
    if payment.invoice_id:
        invoice = db.customer_invoices.find_one({'_id': ObjectId(payment.invoice_id)})
        if invoice:
            response['invoice'] = {
                '_id': str(invoice['_id']),
                'invoice_number': invoice.get('invoice_number'),
                'total_amount': invoice.get('total_amount'),
                'amount_due': invoice.get('amount_due')
            }
    
    if payment.bill_id:
        bill = db.vendor_bills.find_one({'_id': ObjectId(payment.bill_id)})
        if bill:
            response['bill'] = {
                '_id': str(bill['_id']),
                'bill_number': bill.get('bill_number'),
                'total_amount': bill.get('total_amount'),
                'amount_due': bill.get('amount_due')
            }
    
    return jsonify(response), 200

@payments_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_payment():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data.get('payment_type'):
        return jsonify({'error': 'Payment type is required'}), 400
    
    if data['payment_type'] not in Payment.PAYMENT_TYPES:
        return jsonify({'error': f'Invalid payment type. Must be one of: {Payment.PAYMENT_TYPES}'}), 400
    
    if not data.get('amount') or float(data['amount']) <= 0:
        return jsonify({'error': 'Valid amount is required'}), 400
    
    db = get_db()
    
    payment = Payment()
    payment.payment_number = generate_number('PAY', 'payments')
    payment.payment_type = data['payment_type']
    payment.payment_method = data.get('payment_method', Payment.METHOD_BANK_TRANSFER)
    payment.contact_id = data.get('contact_id')
    payment.invoice_id = data.get('invoice_id')
    payment.bill_id = data.get('bill_id')
    payment.payment_date = parse_date(data.get('payment_date')) or datetime.utcnow()
    payment.amount = float(data['amount'])
    payment.reference_number = data.get('reference_number')
    payment.notes = data.get('notes')
    payment.created_by = user_id
    payment.created_at = datetime.utcnow()
    payment.updated_at = datetime.utcnow()
    
    if payment.payment_type == Payment.TYPE_INCOMING and payment.invoice_id:
        invoice = db.customer_invoices.find_one({'_id': ObjectId(payment.invoice_id)})
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        if invoice.get('status') != 'posted':
            return jsonify({'error': 'Can only record payments for posted invoices'}), 400
        
        new_amount_paid = invoice.get('amount_paid', 0) + payment.amount
        new_amount_due = invoice.get('total_amount', 0) - new_amount_paid
        
        if new_amount_paid > invoice.get('total_amount', 0):
            return jsonify({'error': 'Payment amount exceeds invoice balance'}), 400
        
        if new_amount_due <= 0:
            new_payment_status = 'paid'
        elif new_amount_paid > 0:
            new_payment_status = 'partially_paid'
        else:
            new_payment_status = 'not_paid'
        
        payment.contact_id = str(invoice.get('customer_id'))
        
        result = db.payments.insert_one(payment.to_db_dict())
        payment._id = result.inserted_id
        
        db.customer_invoices.update_one(
            {'_id': ObjectId(payment.invoice_id)},
            {'$set': {
                'amount_paid': new_amount_paid,
                'amount_due': new_amount_due,
                'payment_status': new_payment_status,
                'updated_at': datetime.utcnow()
            }}
        )
        
        customer = db.contacts.find_one({'_id': invoice.get('customer_id')})
        if customer and customer.get('email'):
            EmailService.send_payment_confirmation_email(
                customer.get('email'),
                customer.get('name'),
                payment.payment_number,
                payment.amount,
                payment.payment_date.strftime('%Y-%m-%d')
            )
    
    elif payment.payment_type == Payment.TYPE_OUTGOING and payment.bill_id:
        bill = db.vendor_bills.find_one({'_id': ObjectId(payment.bill_id)})
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        if bill.get('status') != 'posted':
            return jsonify({'error': 'Can only record payments for posted bills'}), 400
        
        new_amount_paid = bill.get('amount_paid', 0) + payment.amount
        new_amount_due = bill.get('total_amount', 0) - new_amount_paid
        
        if new_amount_paid > bill.get('total_amount', 0):
            return jsonify({'error': 'Payment amount exceeds bill balance'}), 400
        
        if new_amount_due <= 0:
            new_payment_status = 'paid'
        elif new_amount_paid > 0:
            new_payment_status = 'partially_paid'
        else:
            new_payment_status = 'not_paid'
        
        payment.contact_id = str(bill.get('vendor_id'))
        
        result = db.payments.insert_one(payment.to_db_dict())
        payment._id = result.inserted_id
        
        db.vendor_bills.update_one(
            {'_id': ObjectId(payment.bill_id)},
            {'$set': {
                'amount_paid': new_amount_paid,
                'amount_due': new_amount_due,
                'payment_status': new_payment_status,
                'updated_at': datetime.utcnow()
            }}
        )
    else:
        result = db.payments.insert_one(payment.to_db_dict())
        payment._id = result.inserted_id
    
    return jsonify({
        'message': 'Payment recorded successfully',
        'payment': payment.to_dict()
    }), 201

@payments_bp.route('/<payment_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_payment(payment_id):
    data = request.get_json()
    db = get_db()
    
    payment_data = db.payments.find_one({'_id': ObjectId(payment_id)})
    if not payment_data:
        return jsonify({'error': 'Payment not found'}), 404
    
    if payment_data.get('is_reconciled'):
        return jsonify({'error': 'Cannot modify reconciled payments'}), 400
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'payment_method' in data:
        if data['payment_method'] not in Payment.PAYMENT_METHODS:
            return jsonify({'error': f'Invalid payment method. Must be one of: {Payment.PAYMENT_METHODS}'}), 400
        update_data['payment_method'] = data['payment_method']
    
    if 'payment_date' in data:
        update_data['payment_date'] = parse_date(data['payment_date'])
    
    if 'reference_number' in data:
        update_data['reference_number'] = data['reference_number']
    
    if 'notes' in data:
        update_data['notes'] = data['notes']
    
    db.payments.update_one({'_id': ObjectId(payment_id)}, {'$set': update_data})
    
    updated_payment = db.payments.find_one({'_id': ObjectId(payment_id)})
    
    return jsonify({
        'message': 'Payment updated successfully',
        'payment': Payment.from_db(updated_payment).to_dict()
    }), 200

@payments_bp.route('/<payment_id>/reconcile', methods=['POST'])
@jwt_required()
@admin_required
def reconcile_payment(payment_id):
    db = get_db()
    
    payment_data = db.payments.find_one({'_id': ObjectId(payment_id)})
    if not payment_data:
        return jsonify({'error': 'Payment not found'}), 404
    
    new_status = not payment_data.get('is_reconciled', False)
    
    db.payments.update_one(
        {'_id': ObjectId(payment_id)},
        {'$set': {'is_reconciled': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"Payment {'reconciled' if new_status else 'unreconciled'} successfully",
        'is_reconciled': new_status
    }), 200

@payments_bp.route('/<payment_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_payment(payment_id):
    db = get_db()
    
    payment_data = db.payments.find_one({'_id': ObjectId(payment_id)})
    if not payment_data:
        return jsonify({'error': 'Payment not found'}), 404
    
    if payment_data.get('is_reconciled'):
        return jsonify({'error': 'Cannot delete reconciled payments'}), 400
    
    if payment_data.get('invoice_id'):
        invoice = db.customer_invoices.find_one({'_id': payment_data['invoice_id']})
        if invoice:
            new_amount_paid = invoice.get('amount_paid', 0) - payment_data.get('amount', 0)
            new_amount_due = invoice.get('total_amount', 0) - new_amount_paid
            
            if new_amount_paid <= 0:
                new_payment_status = 'not_paid'
            elif new_amount_paid < invoice.get('total_amount', 0):
                new_payment_status = 'partially_paid'
            else:
                new_payment_status = 'paid'
            
            db.customer_invoices.update_one(
                {'_id': payment_data['invoice_id']},
                {'$set': {
                    'amount_paid': max(0, new_amount_paid),
                    'amount_due': new_amount_due,
                    'payment_status': new_payment_status,
                    'updated_at': datetime.utcnow()
                }}
            )
    
    if payment_data.get('bill_id'):
        bill = db.vendor_bills.find_one({'_id': payment_data['bill_id']})
        if bill:
            new_amount_paid = bill.get('amount_paid', 0) - payment_data.get('amount', 0)
            new_amount_due = bill.get('total_amount', 0) - new_amount_paid
            
            if new_amount_paid <= 0:
                new_payment_status = 'not_paid'
            elif new_amount_paid < bill.get('total_amount', 0):
                new_payment_status = 'partially_paid'
            else:
                new_payment_status = 'paid'
            
            db.vendor_bills.update_one(
                {'_id': payment_data['bill_id']},
                {'$set': {
                    'amount_paid': max(0, new_amount_paid),
                    'amount_due': new_amount_due,
                    'payment_status': new_payment_status,
                    'updated_at': datetime.utcnow()
                }}
            )
    
    db.payments.delete_one({'_id': ObjectId(payment_id)})
    
    return jsonify({'message': 'Payment deleted successfully'}), 200

@payments_bp.route('/methods', methods=['GET'])
@jwt_required()
def get_payment_methods():
    return jsonify({
        'payment_methods': [
            {'value': 'cash', 'label': 'Cash'},
            {'value': 'bank_transfer', 'label': 'Bank Transfer'},
            {'value': 'cheque', 'label': 'Cheque'},
            {'value': 'upi', 'label': 'UPI'},
            {'value': 'card', 'label': 'Card'},
            {'value': 'online', 'label': 'Online Payment'}
        ]
    }), 200
