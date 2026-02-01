from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
import secrets
import string

from app.database import get_db
from app.models.user import User
from app.utils.helpers import admin_required
from app.services.email_service import EmailService

users_bp = Blueprint('users', __name__)

def generate_temp_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(characters) for _ in range(length))

@users_bp.route('', methods=['GET'])
@jwt_required()
@admin_required
def get_users():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    role = request.args.get('role', '')
    
    query = {}
    
    if search:
        query['$or'] = [
            {'email': {'$regex': search, '$options': 'i'}},
            {'full_name': {'$regex': search, '$options': 'i'}}
        ]
    
    if role:
        query['role'] = role
    
    total = db.users.count_documents(query)
    users = list(db.users.find(query).skip((page - 1) * per_page).limit(per_page))
    
    return jsonify({
        'users': [User.from_db(u).to_dict() for u in users],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@users_bp.route('/<user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user(user_id):
    db = get_db()
    
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    user = User.from_db(user_data)
    response = user.to_dict()
    
    if user.contact_id:
        contact = db.contacts.find_one({'_id': ObjectId(user.contact_id)})
        if contact:
            response['contact'] = {
                '_id': str(contact['_id']),
                'name': contact.get('name'),
                'email': contact.get('email')
            }
    
    return jsonify(response), 200

@users_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_user():
    data = request.get_json()
    
    if not data.get('email') or not data.get('full_name') or not data.get('role'):
        return jsonify({'error': 'Email, full name and role are required'}), 400
    
    if data['role'] not in User.ROLES:
        return jsonify({'error': f'Invalid role. Must be one of: {User.ROLES}'}), 400
    
    db = get_db()
    
    if db.users.find_one({'email': data['email'].lower()}):
        return jsonify({'error': 'Email already registered'}), 400
    
    temp_password = data.get('password') or generate_temp_password()
    
    # For portal users and vendors, automatically create a contact
    contact_id = data.get('contact_id')
    if data['role'] in [User.ROLE_PORTAL_USER, User.ROLE_VENDOR] and not contact_id:
        # Determine contact type based on role
        contact_type = 'vendor' if data['role'] == User.ROLE_VENDOR else 'customer'
        
        # Create a contact for this portal user/vendor
        contact_data = {
            'name': data['full_name'],
            'email': data['email'].lower(),
            'phone': data.get('phone', ''),
            'contact_type': contact_type,
            'company_name': '',
            'gstin': '',
            'pan': '',
            'billing_address': {},
            'shipping_address': {},
            'credit_limit': 0,
            'payment_terms': 30,
            'notes': f'Auto-created from user registration ({contact_type})',
            'is_archived': False,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        contact_result = db.contacts.insert_one(contact_data)
        contact_id = str(contact_result.inserted_id)
    
    user = User()
    user.email = data['email'].lower()
    user.full_name = data['full_name']
    user.phone = data.get('phone', '')
    user.set_password(temp_password)
    user.role = data['role']
    user.is_active = data.get('is_active', True)
    user.contact_id = contact_id
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    
    result = db.users.insert_one(user.to_db_dict())
    user._id = result.inserted_id
    
    try:
        if not data.get('password'):
            EmailService.send_welcome_email(user.email, user.full_name, temp_password)
        else:
            EmailService.send_welcome_email(user.email, user.full_name)
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
    
    return jsonify({
        'message': 'User created successfully',
        'user': user.to_dict()
    }), 201

@users_bp.route('/<user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    data = request.get_json()
    db = get_db()
    
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'full_name' in data:
        update_data['full_name'] = data['full_name']
    
    if 'role' in data:
        if data['role'] not in User.ROLES:
            return jsonify({'error': f'Invalid role. Must be one of: {User.ROLES}'}), 400
        update_data['role'] = data['role']
    
    if 'is_active' in data:
        update_data['is_active'] = data['is_active']
    
    if 'contact_id' in data:
        update_data['contact_id'] = ObjectId(data['contact_id']) if data['contact_id'] else None
    
    if 'email' in data and data['email'].lower() != user_data['email']:
        if db.users.find_one({'email': data['email'].lower(), '_id': {'$ne': ObjectId(user_id)}}):
            return jsonify({'error': 'Email already in use'}), 400
        update_data['email'] = data['email'].lower()
    
    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': update_data})
    
    updated_user = db.users.find_one({'_id': ObjectId(user_id)})
    
    return jsonify({
        'message': 'User updated successfully',
        'user': User.from_db(updated_user).to_dict()
    }), 200

@users_bp.route('/<user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    current_user_id = get_jwt_identity()
    
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    db = get_db()
    
    result = db.users.delete_one({'_id': ObjectId(user_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'message': 'User deleted successfully'}), 200

@users_bp.route('/<user_id>/toggle-active', methods=['POST'])
@jwt_required()
@admin_required
def toggle_user_active(user_id):
    current_user_id = get_jwt_identity()
    
    if user_id == current_user_id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    db = get_db()
    
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    new_status = not user_data.get('is_active', True)
    
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'is_active': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"User {'activated' if new_status else 'deactivated'} successfully",
        'is_active': new_status
    }), 200

@users_bp.route('/<user_id>/reset-password', methods=['POST'])
@jwt_required()
@admin_required
def admin_reset_password(user_id):
    db = get_db()
    
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    temp_password = generate_temp_password()
    user = User.from_db(user_data)
    user.set_password(temp_password)
    
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {
            'password_hash': user.password_hash,
            'updated_at': datetime.utcnow()
        }}
    )
    
    EmailService.send_welcome_email(user.email, user.full_name, temp_password)
    
    return jsonify({'message': 'Password reset email sent to user'}), 200
