from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.analytical_account import AnalyticalAccount
from app.utils.helpers import admin_required

analytical_accounts_bp = Blueprint('analytical_accounts', __name__)

@analytical_accounts_bp.route('', methods=['GET'])
@jwt_required()
def get_analytical_accounts():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    search = request.args.get('search', '')
    account_type = request.args.get('type', '')
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    
    query = {}
    
    if not include_archived:
        query['is_archived'] = False
    
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'code': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
    
    if account_type:
        query['account_type'] = {'$in': [account_type, 'both']}
    
    total = db.analytical_accounts.count_documents(query)
    accounts = list(db.analytical_accounts.find(query).sort('code', 1).skip((page - 1) * per_page).limit(per_page))
    
    return jsonify({
        'analytical_accounts': [AnalyticalAccount.from_db(a).to_dict() for a in accounts],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@analytical_accounts_bp.route('/<account_id>', methods=['GET'])
@jwt_required()
def get_analytical_account(account_id):
    db = get_db()
    
    account_data = db.analytical_accounts.find_one({'_id': ObjectId(account_id)})
    if not account_data:
        return jsonify({'error': 'Analytical account not found'}), 404
    
    account = AnalyticalAccount.from_db(account_data)
    response = account.to_dict()
    
    if account.parent_id:
        parent = db.analytical_accounts.find_one({'_id': ObjectId(account.parent_id)})
        if parent:
            response['parent'] = {
                '_id': str(parent['_id']),
                'code': parent.get('code'),
                'name': parent.get('name')
            }
    
    children = list(db.analytical_accounts.find({'parent_id': ObjectId(account_id), 'is_archived': False}))
    response['children'] = [{'_id': str(c['_id']), 'code': c.get('code'), 'name': c.get('name')} for c in children]
    
    budgets = list(db.budgets.find({'analytical_account_id': ObjectId(account_id), 'is_archived': False}))
    response['budgets_count'] = len(budgets)
    
    return jsonify(response), 200

@analytical_accounts_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_analytical_account():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if not data.get('name') or not data.get('code'):
        return jsonify({'error': 'Name and code are required'}), 400
    
    if data.get('account_type') and data['account_type'] not in AnalyticalAccount.ACCOUNT_TYPES:
        return jsonify({'error': f'Invalid account type. Must be one of: {AnalyticalAccount.ACCOUNT_TYPES}'}), 400
    
    db = get_db()
    
    if db.analytical_accounts.find_one({'code': data['code'].upper()}):
        return jsonify({'error': 'Account code already exists'}), 400
    
    account = AnalyticalAccount()
    account.code = data['code'].upper()
    account.name = data['name']
    account.description = data.get('description')
    account.account_type = data.get('account_type', AnalyticalAccount.TYPE_BOTH)
    account.parent_id = data.get('parent_id')
    account.created_by = user_id
    account.created_at = datetime.utcnow()
    account.updated_at = datetime.utcnow()
    
    result = db.analytical_accounts.insert_one(account.to_db_dict())
    account._id = result.inserted_id
    
    return jsonify({
        'message': 'Analytical account created successfully',
        'analytical_account': account.to_dict()
    }), 201

@analytical_accounts_bp.route('/<account_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_analytical_account(account_id):
    data = request.get_json()
    db = get_db()
    
    account_data = db.analytical_accounts.find_one({'_id': ObjectId(account_id)})
    if not account_data:
        return jsonify({'error': 'Analytical account not found'}), 404
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'code' in data and data['code'].upper() != account_data['code']:
        if db.analytical_accounts.find_one({'code': data['code'].upper(), '_id': {'$ne': ObjectId(account_id)}}):
            return jsonify({'error': 'Account code already exists'}), 400
        update_data['code'] = data['code'].upper()
    
    if 'name' in data:
        update_data['name'] = data['name']
    
    if 'description' in data:
        update_data['description'] = data['description']
    
    if 'account_type' in data:
        if data['account_type'] not in AnalyticalAccount.ACCOUNT_TYPES:
            return jsonify({'error': f'Invalid account type. Must be one of: {AnalyticalAccount.ACCOUNT_TYPES}'}), 400
        update_data['account_type'] = data['account_type']
    
    if 'parent_id' in data:
        if data['parent_id'] == account_id:
            return jsonify({'error': 'Account cannot be its own parent'}), 400
        update_data['parent_id'] = ObjectId(data['parent_id']) if data['parent_id'] else None
    
    db.analytical_accounts.update_one({'_id': ObjectId(account_id)}, {'$set': update_data})
    
    updated_account = db.analytical_accounts.find_one({'_id': ObjectId(account_id)})
    
    return jsonify({
        'message': 'Analytical account updated successfully',
        'analytical_account': AnalyticalAccount.from_db(updated_account).to_dict()
    }), 200

@analytical_accounts_bp.route('/<account_id>/archive', methods=['POST'])
@jwt_required()
@admin_required
def archive_analytical_account(account_id):
    db = get_db()
    
    account_data = db.analytical_accounts.find_one({'_id': ObjectId(account_id)})
    if not account_data:
        return jsonify({'error': 'Analytical account not found'}), 404
    
    new_status = not account_data.get('is_archived', False)
    
    db.analytical_accounts.update_one(
        {'_id': ObjectId(account_id)},
        {'$set': {'is_archived': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"Analytical account {'archived' if new_status else 'unarchived'} successfully",
        'is_archived': new_status
    }), 200

@analytical_accounts_bp.route('/<account_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_analytical_account(account_id):
    db = get_db()
    
    has_budgets = db.budgets.find_one({'analytical_account_id': ObjectId(account_id)})
    has_children = db.analytical_accounts.find_one({'parent_id': ObjectId(account_id)})
    
    if has_budgets or has_children:
        return jsonify({'error': 'Cannot delete account with budgets or child accounts. Archive instead.'}), 400
    
    result = db.analytical_accounts.delete_one({'_id': ObjectId(account_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Analytical account not found'}), 404
    
    return jsonify({'message': 'Analytical account deleted successfully'}), 200

@analytical_accounts_bp.route('/tree', methods=['GET'])
@jwt_required()
def get_accounts_tree():
    db = get_db()
    
    accounts = list(db.analytical_accounts.find({'is_archived': False}).sort('code', 1))
    
    def build_tree(parent_id=None):
        children = []
        for account in accounts:
            acc_parent = account.get('parent_id')
            if (parent_id is None and acc_parent is None) or (acc_parent and str(acc_parent) == str(parent_id)):
                node = {
                    '_id': str(account['_id']),
                    'code': account.get('code'),
                    'name': account.get('name'),
                    'account_type': account.get('account_type'),
                    'children': build_tree(account['_id'])
                }
                children.append(node)
        return children
    
    tree = build_tree()
    
    return jsonify({'tree': tree}), 200
