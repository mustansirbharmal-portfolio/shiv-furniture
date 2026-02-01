from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.auto_analytical_model import AutoAnalyticalModel
from app.utils.helpers import admin_required
from app.services.openai_service import OpenAIService

auto_analytical_models_bp = Blueprint('auto_analytical_models', __name__)

@auto_analytical_models_bp.route('', methods=['GET'])
@jwt_required()
def get_models():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    rule_type = request.args.get('rule_type', '')
    is_active = request.args.get('is_active', '')
    
    query = {}
    
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    if rule_type:
        query['rule_type'] = rule_type
    
    if is_active:
        query['is_active'] = is_active.lower() == 'true'
    
    total = db.auto_analytical_models.count_documents(query)
    models = list(db.auto_analytical_models.find(query).sort('priority', -1).skip((page - 1) * per_page).limit(per_page))
    
    model_list = []
    for model_data in models:
        model = AutoAnalyticalModel.from_db(model_data)
        model_dict = model.to_dict()
        
        if model.analytical_account_id:
            account = db.analytical_accounts.find_one({'_id': ObjectId(model.analytical_account_id)})
            if account:
                model_dict['analytical_account'] = {
                    '_id': str(account['_id']),
                    'code': account.get('code'),
                    'name': account.get('name')
                }
        
        model_list.append(model_dict)
    
    return jsonify({
        'models': model_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@auto_analytical_models_bp.route('/<model_id>', methods=['GET'])
@jwt_required()
def get_model(model_id):
    db = get_db()
    
    model_data = db.auto_analytical_models.find_one({'_id': ObjectId(model_id)})
    if not model_data:
        return jsonify({'error': 'Model not found'}), 404
    
    model = AutoAnalyticalModel.from_db(model_data)
    response = model.to_dict()
    
    if model.analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(model.analytical_account_id)})
        if account:
            response['analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    return jsonify(response), 200

@auto_analytical_models_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_model():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    required_fields = ['name', 'rule_type', 'rule_value', 'analytical_account_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    if data['rule_type'] not in AutoAnalyticalModel.RULE_TYPES:
        return jsonify({'error': f'Invalid rule type. Must be one of: {AutoAnalyticalModel.RULE_TYPES}'}), 400
    
    db = get_db()
    
    if not db.analytical_accounts.find_one({'_id': ObjectId(data['analytical_account_id'])}):
        return jsonify({'error': 'Analytical account not found'}), 404
    
    model = AutoAnalyticalModel()
    model.name = data['name']
    model.description = data.get('description')
    model.rule_type = data['rule_type']
    model.rule_value = data['rule_value']
    model.analytical_account_id = data['analytical_account_id']
    model.priority = int(data.get('priority', 0))
    model.is_active = data.get('is_active', True)
    model.created_by = user_id
    model.created_at = datetime.utcnow()
    model.updated_at = datetime.utcnow()
    
    result = db.auto_analytical_models.insert_one(model.to_db_dict())
    model._id = result.inserted_id
    
    return jsonify({
        'message': 'Auto analytical model created successfully',
        'model': model.to_dict()
    }), 201

@auto_analytical_models_bp.route('/<model_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_model(model_id):
    data = request.get_json()
    db = get_db()
    
    model_data = db.auto_analytical_models.find_one({'_id': ObjectId(model_id)})
    if not model_data:
        return jsonify({'error': 'Model not found'}), 404
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'name' in data:
        update_data['name'] = data['name']
    
    if 'description' in data:
        update_data['description'] = data['description']
    
    if 'rule_type' in data:
        if data['rule_type'] not in AutoAnalyticalModel.RULE_TYPES:
            return jsonify({'error': f'Invalid rule type. Must be one of: {AutoAnalyticalModel.RULE_TYPES}'}), 400
        update_data['rule_type'] = data['rule_type']
    
    if 'rule_value' in data:
        update_data['rule_value'] = data['rule_value']
    
    if 'analytical_account_id' in data:
        if not db.analytical_accounts.find_one({'_id': ObjectId(data['analytical_account_id'])}):
            return jsonify({'error': 'Analytical account not found'}), 404
        update_data['analytical_account_id'] = ObjectId(data['analytical_account_id'])
    
    if 'priority' in data:
        update_data['priority'] = int(data['priority'])
    
    if 'is_active' in data:
        update_data['is_active'] = data['is_active']
    
    db.auto_analytical_models.update_one({'_id': ObjectId(model_id)}, {'$set': update_data})
    
    updated_model = db.auto_analytical_models.find_one({'_id': ObjectId(model_id)})
    
    return jsonify({
        'message': 'Model updated successfully',
        'model': AutoAnalyticalModel.from_db(updated_model).to_dict()
    }), 200

@auto_analytical_models_bp.route('/<model_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_model(model_id):
    db = get_db()
    
    result = db.auto_analytical_models.delete_one({'_id': ObjectId(model_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Model not found'}), 404
    
    return jsonify({'message': 'Model deleted successfully'}), 200

@auto_analytical_models_bp.route('/<model_id>/toggle-active', methods=['POST'])
@jwt_required()
@admin_required
def toggle_model_active(model_id):
    db = get_db()
    
    model_data = db.auto_analytical_models.find_one({'_id': ObjectId(model_id)})
    if not model_data:
        return jsonify({'error': 'Model not found'}), 404
    
    new_status = not model_data.get('is_active', True)
    
    db.auto_analytical_models.update_one(
        {'_id': ObjectId(model_id)},
        {'$set': {'is_active': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"Model {'activated' if new_status else 'deactivated'} successfully",
        'is_active': new_status
    }), 200

@auto_analytical_models_bp.route('/rule-types', methods=['GET'])
@jwt_required()
def get_rule_types():
    return jsonify({
        'rule_types': [
            {'value': 'product_category', 'label': 'Product Category', 'description': 'Match by product category'},
            {'value': 'product', 'label': 'Specific Product', 'description': 'Match by specific product ID'},
            {'value': 'contact', 'label': 'Contact', 'description': 'Match by contact/vendor/customer ID'},
            {'value': 'amount_range', 'label': 'Amount Range', 'description': 'Match by transaction amount range (e.g., 1000-5000)'}
        ]
    }), 200

@auto_analytical_models_bp.route('/suggest-rule-value', methods=['POST'])
@jwt_required()
def suggest_rule_value():
    """Use AI to suggest a rule value based on model name and rule type"""
    data = request.get_json()
    
    model_name = data.get('name', '')
    rule_type = data.get('rule_type', 'product_category')
    
    if not model_name:
        return jsonify({'error': 'Model name is required'}), 400
    
    if not OpenAIService.is_configured():
        return jsonify({'error': 'AI service not configured', 'suggestion': None}), 200
    
    suggestion = OpenAIService.generate_rule_value(model_name, rule_type)
    
    return jsonify({
        'suggestion': suggestion,
        'model_name': model_name,
        'rule_type': rule_type
    }), 200
