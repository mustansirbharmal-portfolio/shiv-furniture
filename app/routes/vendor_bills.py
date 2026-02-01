from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from bson import ObjectId

from app.database import get_db
from app.models.vendor_bill import VendorBill
from app.utils.helpers import admin_required, generate_number, parse_date
from app.services.analytics_service import AnalyticsService
from app.services.pdf_service import PDFService
from app.services.file_service import FileService

vendor_bills_bp = Blueprint('vendor_bills', __name__)

@vendor_bills_bp.route('', methods=['GET'])
@jwt_required()
def get_vendor_bills():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    payment_status = request.args.get('payment_status', '')
    vendor_id = request.args.get('vendor_id', '')
    
    query = {}
    
    if search:
        query['$or'] = [
            {'bill_number': {'$regex': search, '$options': 'i'}},
            {'vendor_bill_number': {'$regex': search, '$options': 'i'}}
        ]
    
    if status:
        query['status'] = status
    
    if payment_status:
        query['payment_status'] = payment_status
    
    if vendor_id:
        query['vendor_id'] = ObjectId(vendor_id)
    
    total = db.vendor_bills.count_documents(query)
    bills = list(db.vendor_bills.find(query).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    bill_list = []
    for bill_data in bills:
        bill = VendorBill.from_db(bill_data)
        bill_dict = bill.to_dict()
        
        if bill.vendor_id:
            vendor = db.contacts.find_one({'_id': ObjectId(bill.vendor_id)})
            if vendor:
                bill_dict['vendor'] = {
                    '_id': str(vendor['_id']),
                    'name': vendor.get('name'),
                    'company_name': vendor.get('company_name')
                }
        
        bill_list.append(bill_dict)
    
    return jsonify({
        'vendor_bills': bill_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@vendor_bills_bp.route('/<bill_id>', methods=['GET'])
@jwt_required()
def get_vendor_bill(bill_id):
    db = get_db()
    
    bill_data = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    if not bill_data:
        return jsonify({'error': 'Vendor bill not found'}), 404
    
    bill = VendorBill.from_db(bill_data)
    response = bill.to_dict()
    
    if bill.vendor_id:
        vendor = db.contacts.find_one({'_id': ObjectId(bill.vendor_id)})
        if vendor:
            response['vendor'] = {
                '_id': str(vendor['_id']),
                'name': vendor.get('name'),
                'company_name': vendor.get('company_name'),
                'email': vendor.get('email'),
                'phone': vendor.get('phone')
            }
    
    if bill.purchase_order_id:
        po = db.purchase_orders.find_one({'_id': ObjectId(bill.purchase_order_id)})
        if po:
            response['purchase_order'] = {
                '_id': str(po['_id']),
                'po_number': po.get('po_number')
            }
    
    if bill.analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(bill.analytical_account_id)})
        if account:
            response['analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    payments = list(db.payments.find({'bill_id': ObjectId(bill_id)}))
    response['payments'] = [{
        '_id': str(p['_id']),
        'payment_number': p.get('payment_number'),
        'amount': p.get('amount'),
        'payment_date': p.get('payment_date').isoformat() if p.get('payment_date') else None,
        'payment_method': p.get('payment_method')
    } for p in payments]
    
    return jsonify(response), 200

@vendor_bills_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_vendor_bill():
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
    
    bill = VendorBill()
    bill.bill_number = generate_number('BILL', 'vendor_bills')
    bill.vendor_bill_number = data.get('vendor_bill_number')
    bill.vendor_id = data['vendor_id']
    bill.purchase_order_id = data.get('purchase_order_id')
    bill.bill_date = parse_date(data.get('bill_date')) or datetime.utcnow()
    bill.due_date = parse_date(data.get('due_date')) or (bill.bill_date + timedelta(days=vendor.get('payment_terms', 30)))
    bill.status = VendorBill.STATUS_DRAFT
    bill.payment_status = VendorBill.PAYMENT_STATUS_NOT_PAID
    bill.notes = data.get('notes')
    bill.created_by = user_id
    bill.created_at = datetime.utcnow()
    bill.updated_at = datetime.utcnow()
    
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
    
    bill.items = items
    bill.calculate_totals()
    
    analytical_account_id = data.get('analytical_account_id')
    if not analytical_account_id and items:
        first_product = db.products.find_one({'_id': ObjectId(items[0]['product_id'])})
        if first_product:
            analytical_account_id = AnalyticsService.get_analytical_account_for_transaction(
                product_id=first_product['_id'],
                category=first_product.get('category'),
                contact_id=data['vendor_id'],
                amount=bill.total_amount
            )
    
    if analytical_account_id:
        bill.analytical_account_id = str(analytical_account_id)
    
    result = db.vendor_bills.insert_one(bill.to_db_dict())
    bill._id = result.inserted_id
    
    return jsonify({
        'message': 'Vendor bill created successfully',
        'vendor_bill': bill.to_dict()
    }), 201

@vendor_bills_bp.route('/<bill_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_vendor_bill(bill_id):
    data = request.get_json()
    db = get_db()
    
    bill_data = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    if not bill_data:
        return jsonify({'error': 'Vendor bill not found'}), 404
    
    if bill_data.get('status') != VendorBill.STATUS_DRAFT:
        return jsonify({'error': 'Only draft bills can be modified'}), 400
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'vendor_id' in data:
        vendor = db.contacts.find_one({'_id': ObjectId(data['vendor_id'])})
        if not vendor:
            return jsonify({'error': 'Vendor not found'}), 404
        update_data['vendor_id'] = ObjectId(data['vendor_id'])
    
    if 'vendor_bill_number' in data:
        update_data['vendor_bill_number'] = data['vendor_bill_number']
    
    if 'bill_date' in data:
        update_data['bill_date'] = parse_date(data['bill_date'])
    
    if 'due_date' in data:
        update_data['due_date'] = parse_date(data['due_date'])
    
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
        update_data['amount_due'] = subtotal + tax_amount - bill_data.get('amount_paid', 0)
    
    db.vendor_bills.update_one({'_id': ObjectId(bill_id)}, {'$set': update_data})
    
    updated_bill = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    
    return jsonify({
        'message': 'Vendor bill updated successfully',
        'vendor_bill': VendorBill.from_db(updated_bill).to_dict()
    }), 200

@vendor_bills_bp.route('/<bill_id>/post', methods=['POST'])
@jwt_required()
@admin_required
def post_vendor_bill(bill_id):
    db = get_db()
    
    bill_data = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    if not bill_data:
        return jsonify({'error': 'Vendor bill not found'}), 404
    
    if bill_data.get('status') != VendorBill.STATUS_DRAFT:
        return jsonify({'error': 'Only draft bills can be posted'}), 400
    
    db.vendor_bills.update_one(
        {'_id': ObjectId(bill_id)},
        {'$set': {'status': VendorBill.STATUS_POSTED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Vendor bill posted successfully'}), 200

@vendor_bills_bp.route('/<bill_id>/cancel', methods=['POST'])
@jwt_required()
@admin_required
def cancel_vendor_bill(bill_id):
    db = get_db()
    
    bill_data = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    if not bill_data:
        return jsonify({'error': 'Vendor bill not found'}), 404
    
    if bill_data.get('status') == VendorBill.STATUS_CANCELLED:
        return jsonify({'error': 'Bill is already cancelled'}), 400
    
    if bill_data.get('amount_paid', 0) > 0:
        return jsonify({'error': 'Cannot cancel bill with payments'}), 400
    
    db.vendor_bills.update_one(
        {'_id': ObjectId(bill_id)},
        {'$set': {'status': VendorBill.STATUS_CANCELLED, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({'message': 'Vendor bill cancelled successfully'}), 200

@vendor_bills_bp.route('/<bill_id>/pdf', methods=['GET'])
@jwt_required()
def generate_bill_pdf(bill_id):
    db = get_db()
    
    bill_data = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    if not bill_data:
        return jsonify({'error': 'Vendor bill not found'}), 404
    
    bill = VendorBill.from_db(bill_data)
    
    vendor = db.contacts.find_one({'_id': ObjectId(bill.vendor_id)}) if bill.vendor_id else {}
    
    bill_dict = bill.to_dict()
    bill_dict['bill_date'] = bill.bill_date.strftime('%Y-%m-%d') if bill.bill_date else ''
    bill_dict['due_date'] = bill.due_date.strftime('%Y-%m-%d') if bill.due_date else ''
    
    pdf_content = PDFService.generate_vendor_bill_pdf(bill_dict, vendor, bill.items)
    
    result = FileService.upload_file_with_sas_url(
        pdf_content,
        f"Bill_{bill.bill_number}.pdf",
        'vendor_bills',
        'application/pdf'
    )
    
    if result['success']:
        db.vendor_bills.update_one(
            {'_id': ObjectId(bill_id)},
            {'$set': {'document_url': result['url'], 'blob_name': result['blob_name']}}
        )
        return jsonify({'url': result['url']}), 200
    else:
        return jsonify({'error': 'Failed to generate PDF'}), 500

@vendor_bills_bp.route('/<bill_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_vendor_bill(bill_id):
    db = get_db()
    
    bill_data = db.vendor_bills.find_one({'_id': ObjectId(bill_id)})
    if not bill_data:
        return jsonify({'error': 'Vendor bill not found'}), 404
    
    if bill_data.get('status') != VendorBill.STATUS_DRAFT:
        return jsonify({'error': 'Only draft bills can be deleted'}), 400
    
    db.vendor_bills.delete_one({'_id': ObjectId(bill_id)})
    
    return jsonify({'message': 'Vendor bill deleted successfully'}), 200
