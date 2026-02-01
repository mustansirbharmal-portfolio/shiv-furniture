from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.contact import Contact
from app.utils.helpers import admin_required

contacts_bp = Blueprint('contacts', __name__)

@contacts_bp.route('', methods=['GET'])
@jwt_required()
def get_contacts():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    contact_type = request.args.get('type', '')
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    
    query = {}
    
    if not include_archived:
        query['is_archived'] = False
    
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'company_name': {'$regex': search, '$options': 'i'}},
            {'phone': {'$regex': search, '$options': 'i'}}
        ]
    
    if contact_type:
        if contact_type in ['customer', 'vendor']:
            query['contact_type'] = {'$in': [contact_type, 'both']}
        else:
            query['contact_type'] = contact_type
    
    total = db.contacts.count_documents(query)
    contacts = list(db.contacts.find(query).sort('name', 1).skip((page - 1) * per_page).limit(per_page))
    
    return jsonify({
        'contacts': [Contact.from_db(c).to_dict() for c in contacts],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@contacts_bp.route('/<contact_id>', methods=['GET'])
@jwt_required()
def get_contact(contact_id):
    db = get_db()
    
    contact_data = db.contacts.find_one({'_id': ObjectId(contact_id)})
    if not contact_data:
        return jsonify({'error': 'Contact not found'}), 404
    
    contact = Contact.from_db(contact_data)
    response = contact.to_dict()
    
    user = db.users.find_one({'contact_id': ObjectId(contact_id)})
    if user:
        response['has_portal_access'] = True
        response['user_id'] = str(user['_id'])
    else:
        response['has_portal_access'] = False
    
    return jsonify(response), 200

@contacts_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_contact():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    if data.get('contact_type') and data['contact_type'] not in Contact.CONTACT_TYPES:
        return jsonify({'error': f'Invalid contact type. Must be one of: {Contact.CONTACT_TYPES}'}), 400
    
    db = get_db()
    
    contact = Contact()
    contact.name = data['name']
    contact.email = data.get('email', '').lower() if data.get('email') else None
    contact.phone = data.get('phone')
    contact.contact_type = data.get('contact_type', Contact.TYPE_CUSTOMER)
    contact.company_name = data.get('company_name')
    contact.gstin = data.get('gstin')
    contact.pan = data.get('pan')
    contact.billing_address = data.get('billing_address', {})
    contact.shipping_address = data.get('shipping_address', {})
    contact.credit_limit = data.get('credit_limit', 0)
    contact.payment_terms = data.get('payment_terms', 30)
    contact.notes = data.get('notes')
    contact.created_by = user_id
    contact.created_at = datetime.utcnow()
    contact.updated_at = datetime.utcnow()
    
    result = db.contacts.insert_one(contact.to_db_dict())
    contact._id = result.inserted_id
    
    return jsonify({
        'message': 'Contact created successfully',
        'contact': contact.to_dict()
    }), 201

@contacts_bp.route('/<contact_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_contact(contact_id):
    data = request.get_json()
    db = get_db()
    
    contact_data = db.contacts.find_one({'_id': ObjectId(contact_id)})
    if not contact_data:
        return jsonify({'error': 'Contact not found'}), 404
    
    update_data = {'updated_at': datetime.utcnow()}
    
    allowed_fields = ['name', 'email', 'phone', 'contact_type', 'company_name', 
                      'gstin', 'pan', 'billing_address', 'shipping_address',
                      'credit_limit', 'payment_terms', 'notes']
    
    for field in allowed_fields:
        if field in data:
            if field == 'email':
                update_data[field] = data[field].lower() if data[field] else None
            elif field == 'contact_type':
                if data[field] not in Contact.CONTACT_TYPES:
                    return jsonify({'error': f'Invalid contact type. Must be one of: {Contact.CONTACT_TYPES}'}), 400
                update_data[field] = data[field]
            else:
                update_data[field] = data[field]
    
    db.contacts.update_one({'_id': ObjectId(contact_id)}, {'$set': update_data})
    
    updated_contact = db.contacts.find_one({'_id': ObjectId(contact_id)})
    
    return jsonify({
        'message': 'Contact updated successfully',
        'contact': Contact.from_db(updated_contact).to_dict()
    }), 200

@contacts_bp.route('/<contact_id>/archive', methods=['POST'])
@jwt_required()
@admin_required
def archive_contact(contact_id):
    db = get_db()
    
    contact_data = db.contacts.find_one({'_id': ObjectId(contact_id)})
    if not contact_data:
        return jsonify({'error': 'Contact not found'}), 404
    
    new_status = not contact_data.get('is_archived', False)
    
    db.contacts.update_one(
        {'_id': ObjectId(contact_id)},
        {'$set': {'is_archived': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"Contact {'archived' if new_status else 'unarchived'} successfully",
        'is_archived': new_status
    }), 200

@contacts_bp.route('/<contact_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_contact(contact_id):
    db = get_db()
    
    has_transactions = (
        db.purchase_orders.find_one({'vendor_id': ObjectId(contact_id)}) or
        db.vendor_bills.find_one({'vendor_id': ObjectId(contact_id)}) or
        db.sales_orders.find_one({'customer_id': ObjectId(contact_id)}) or
        db.customer_invoices.find_one({'customer_id': ObjectId(contact_id)})
    )
    
    if has_transactions:
        return jsonify({'error': 'Cannot delete contact with existing transactions. Archive instead.'}), 400
    
    result = db.contacts.delete_one({'_id': ObjectId(contact_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Contact not found'}), 404
    
    db.users.delete_many({'contact_id': ObjectId(contact_id)})
    
    return jsonify({'message': 'Contact deleted successfully'}), 200

@contacts_bp.route('/customers', methods=['GET'])
@jwt_required()
def get_customers():
    db = get_db()
    
    query = {
        'is_archived': False,
        'contact_type': {'$in': ['customer', 'both']}
    }
    
    contacts = list(db.contacts.find(query).sort('name', 1))
    
    return jsonify({
        'customers': [Contact.from_db(c).to_dict() for c in contacts]
    }), 200

@contacts_bp.route('/vendors', methods=['GET'])
@jwt_required()
def get_vendors():
    db = get_db()
    
    query = {
        'is_archived': False,
        'contact_type': {'$in': ['vendor', 'both']}
    }
    
    contacts = list(db.contacts.find(query).sort('name', 1))
    
    return jsonify({
        'vendors': [Contact.from_db(c).to_dict() for c in contacts]
    }), 200
