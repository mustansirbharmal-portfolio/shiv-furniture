from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from bson import ObjectId
import secrets

from app.database import get_db
from app.models.user import User
from app.services.email_service import EmailService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password') or not data.get('full_name'):
        return jsonify({'error': 'Email, password and full name are required'}), 400
    
    db = get_db()
    
    if db.users.find_one({'email': data['email'].lower()}):
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User()
    user.email = data['email'].lower()
    user.full_name = data['full_name']
    user.set_password(data['password'])
    user.role = User.ROLE_PORTAL_USER
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    
    result = db.users.insert_one(user.to_db_dict())
    user._id = result.inserted_id
    
    EmailService.send_welcome_email(user.email, user.full_name)
    
    access_token = create_access_token(identity=str(user._id))
    refresh_token = create_refresh_token(identity=str(user._id))
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    db = get_db()
    user_data = db.users.find_one({'email': data['email'].lower()})
    
    if not user_data:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    user = User.from_db(user_data)
    
    if not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 401
    
    db.users.update_one(
        {'_id': user._id},
        {'$set': {'last_login': datetime.utcnow()}}
    )
    
    access_token = create_access_token(identity=str(user._id))
    refresh_token = create_refresh_token(identity=str(user._id))
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({'access_token': access_token}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    db = get_db()
    
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    user = User.from_db(user_data)
    
    response_data = user.to_dict()
    
    if user.contact_id:
        contact = db.contacts.find_one({'_id': ObjectId(user.contact_id)})
        if contact:
            response_data['contact'] = {
                '_id': str(contact['_id']),
                'name': contact.get('name'),
                'email': contact.get('email'),
                'company_name': contact.get('company_name')
            }
    
    return jsonify(response_data), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    db = get_db()
    user_data = db.users.find_one({'email': data['email'].lower()})
    
    if not user_data:
        return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200
    
    reset_token = secrets.token_urlsafe(32)
    reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    db.users.update_one(
        {'_id': user_data['_id']},
        {'$set': {
            'password_reset_token': reset_token,
            'password_reset_expires': reset_expires
        }}
    )
    
    user = User.from_db(user_data)
    EmailService.send_password_reset_email(user.email, user.full_name, reset_token)
    
    return jsonify({'message': 'If the email exists, a reset link has been sent'}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    
    if not data.get('token') or not data.get('password'):
        return jsonify({'error': 'Token and new password are required'}), 400
    
    db = get_db()
    user_data = db.users.find_one({
        'password_reset_token': data['token'],
        'password_reset_expires': {'$gt': datetime.utcnow()}
    })
    
    if not user_data:
        return jsonify({'error': 'Invalid or expired reset token'}), 400
    
    user = User.from_db(user_data)
    user.set_password(data['password'])
    
    db.users.update_one(
        {'_id': user._id},
        {'$set': {
            'password_hash': user.password_hash,
            'password_reset_token': None,
            'password_reset_expires': None,
            'updated_at': datetime.utcnow()
        }}
    )
    
    return jsonify({'message': 'Password reset successful'}), 200

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Current and new password are required'}), 400
    
    db = get_db()
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    user = User.from_db(user_data)
    
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    user.set_password(data['new_password'])
    
    db.users.update_one(
        {'_id': user._id},
        {'$set': {
            'password_hash': user.password_hash,
            'updated_at': datetime.utcnow()
        }}
    )
    
    return jsonify({'message': 'Password changed successfully'}), 200
