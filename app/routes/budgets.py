from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.models.budget import Budget, BudgetRevision
from app.utils.helpers import admin_required, parse_date
from app.services.analytics_service import AnalyticsService

budgets_bp = Blueprint('budgets', __name__)

@budgets_bp.route('', methods=['GET'])
@jwt_required()
def get_budgets():
    db = get_db()
    
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '')
    budget_type = request.args.get('type', '')
    analytical_account_id = request.args.get('analytical_account_id', '')
    include_archived = request.args.get('include_archived', 'false').lower() == 'true'
    
    query = {}
    
    if not include_archived:
        query['is_archived'] = False
    
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    if budget_type:
        query['budget_type'] = budget_type
    
    if analytical_account_id:
        query['analytical_account_id'] = ObjectId(analytical_account_id)
    
    total = db.budgets.count_documents(query)
    budgets = list(db.budgets.find(query).sort('created_at', -1).skip((page - 1) * per_page).limit(per_page))
    
    budget_list = []
    for budget_data in budgets:
        budget = Budget.from_db(budget_data)
        budget_dict = budget.to_dict()
        
        if budget.analytical_account_id:
            account = db.analytical_accounts.find_one({'_id': ObjectId(budget.analytical_account_id)})
            if account:
                budget_dict['analytical_account'] = {
                    '_id': str(account['_id']),
                    'code': account.get('code'),
                    'name': account.get('name')
                }
        
        performance = AnalyticsService.calculate_budget_actuals(budget._id)
        if performance:
            budget_dict['actual_amount'] = performance['actual_amount']
            budget_dict['remaining_balance'] = performance['remaining_balance']
            budget_dict['achievement_percentage'] = performance['achievement_percentage']
        
        budget_list.append(budget_dict)
    
    return jsonify({
        'budgets': budget_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@budgets_bp.route('/<budget_id>', methods=['GET'])
@jwt_required()
def get_budget(budget_id):
    db = get_db()
    
    budget_data = db.budgets.find_one({'_id': ObjectId(budget_id)})
    if not budget_data:
        return jsonify({'error': 'Budget not found'}), 404
    
    budget = Budget.from_db(budget_data)
    response = budget.to_dict()
    
    if budget.analytical_account_id:
        account = db.analytical_accounts.find_one({'_id': ObjectId(budget.analytical_account_id)})
        if account:
            response['analytical_account'] = {
                '_id': str(account['_id']),
                'code': account.get('code'),
                'name': account.get('name')
            }
    
    performance = AnalyticsService.calculate_budget_actuals(budget._id)
    if performance:
        response['actual_amount'] = performance['actual_amount']
        response['remaining_balance'] = performance['remaining_balance']
        response['achievement_percentage'] = performance['achievement_percentage']
        response['variance'] = performance['variance']
    
    revisions = list(db.budget_revisions.find({'budget_id': ObjectId(budget_id)}).sort('created_at', -1))
    response['revisions'] = [BudgetRevision.from_db(r).to_dict() for r in revisions]
    
    return jsonify(response), 200

@budgets_bp.route('', methods=['POST'])
@jwt_required()
@admin_required
def create_budget():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    required_fields = ['name', 'analytical_account_id', 'budget_type', 'period_start', 'period_end', 'budgeted_amount']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    if data['budget_type'] not in Budget.BUDGET_TYPES:
        return jsonify({'error': f'Invalid budget type. Must be one of: {Budget.BUDGET_TYPES}'}), 400
    
    db = get_db()
    
    if not db.analytical_accounts.find_one({'_id': ObjectId(data['analytical_account_id'])}):
        return jsonify({'error': 'Analytical account not found'}), 404
    
    budget = Budget()
    budget.name = data['name']
    budget.analytical_account_id = data['analytical_account_id']
    budget.budget_type = data['budget_type']
    budget.period_start = parse_date(data['period_start'])
    budget.period_end = parse_date(data['period_end'])
    budget.budgeted_amount = float(data['budgeted_amount'])
    budget.description = data.get('description')
    budget.created_by = user_id
    budget.created_at = datetime.utcnow()
    budget.updated_at = datetime.utcnow()
    
    if budget.period_start >= budget.period_end:
        return jsonify({'error': 'Period end must be after period start'}), 400
    
    result = db.budgets.insert_one(budget.to_db_dict())
    budget._id = result.inserted_id
    
    return jsonify({
        'message': 'Budget created successfully',
        'budget': budget.to_dict()
    }), 201

@budgets_bp.route('/<budget_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_budget(budget_id):
    data = request.get_json()
    user_id = get_jwt_identity()
    db = get_db()
    
    budget_data = db.budgets.find_one({'_id': ObjectId(budget_id)})
    if not budget_data:
        return jsonify({'error': 'Budget not found'}), 404
    
    update_data = {'updated_at': datetime.utcnow()}
    
    if 'name' in data:
        update_data['name'] = data['name']
    
    if 'description' in data:
        update_data['description'] = data['description']
    
    if 'analytical_account_id' in data:
        if not db.analytical_accounts.find_one({'_id': ObjectId(data['analytical_account_id'])}):
            return jsonify({'error': 'Analytical account not found'}), 404
        update_data['analytical_account_id'] = ObjectId(data['analytical_account_id'])
    
    if 'budget_type' in data:
        if data['budget_type'] not in Budget.BUDGET_TYPES:
            return jsonify({'error': f'Invalid budget type. Must be one of: {Budget.BUDGET_TYPES}'}), 400
        update_data['budget_type'] = data['budget_type']
    
    if 'period_start' in data:
        update_data['period_start'] = parse_date(data['period_start'])
    
    if 'period_end' in data:
        update_data['period_end'] = parse_date(data['period_end'])
    
    if 'budgeted_amount' in data:
        old_amount = budget_data.get('budgeted_amount', 0)
        new_amount = float(data['budgeted_amount'])
        
        if old_amount != new_amount:
            revision = BudgetRevision()
            revision.budget_id = budget_id
            revision.previous_amount = old_amount
            revision.new_amount = new_amount
            revision.reason = data.get('revision_reason', 'Budget amount updated')
            revision.revised_by = user_id
            revision.created_at = datetime.utcnow()
            
            db.budget_revisions.insert_one(revision.to_db_dict())
        
        update_data['budgeted_amount'] = new_amount
    
    db.budgets.update_one({'_id': ObjectId(budget_id)}, {'$set': update_data})
    
    updated_budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
    
    return jsonify({
        'message': 'Budget updated successfully',
        'budget': Budget.from_db(updated_budget).to_dict()
    }), 200

@budgets_bp.route('/<budget_id>/archive', methods=['POST'])
@jwt_required()
@admin_required
def archive_budget(budget_id):
    db = get_db()
    
    budget_data = db.budgets.find_one({'_id': ObjectId(budget_id)})
    if not budget_data:
        return jsonify({'error': 'Budget not found'}), 404
    
    new_status = not budget_data.get('is_archived', False)
    
    db.budgets.update_one(
        {'_id': ObjectId(budget_id)},
        {'$set': {'is_archived': new_status, 'updated_at': datetime.utcnow()}}
    )
    
    return jsonify({
        'message': f"Budget {'archived' if new_status else 'unarchived'} successfully",
        'is_archived': new_status
    }), 200

@budgets_bp.route('/<budget_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_budget(budget_id):
    db = get_db()
    
    result = db.budgets.delete_one({'_id': ObjectId(budget_id)})
    
    if result.deleted_count == 0:
        return jsonify({'error': 'Budget not found'}), 404
    
    db.budget_revisions.delete_many({'budget_id': ObjectId(budget_id)})
    
    return jsonify({'message': 'Budget deleted successfully'}), 200

@budgets_bp.route('/<budget_id>/performance', methods=['GET'])
@jwt_required()
def get_budget_performance(budget_id):
    db = get_db()
    
    budget_data = db.budgets.find_one({'_id': ObjectId(budget_id)})
    if not budget_data:
        return jsonify({'error': 'Budget not found'}), 404
    
    performance = AnalyticsService.calculate_budget_actuals(budget_id)
    
    if not performance:
        return jsonify({'error': 'Could not calculate budget performance'}), 500
    
    return jsonify(performance), 200

@budgets_bp.route('/performance', methods=['GET'])
@jwt_required()
def get_all_budgets_performance():
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    start_date = parse_date(period_start) if period_start else None
    end_date = parse_date(period_end) if period_end else None
    
    performance = AnalyticsService.get_all_budgets_performance(start_date, end_date)
    
    return jsonify({
        'budgets_performance': performance,
        'summary': {
            'total_budgeted': sum(p['budgeted_amount'] for p in performance),
            'total_actual': sum(p['actual_amount'] for p in performance),
            'total_remaining': sum(p['remaining_balance'] for p in performance),
            'budgets_on_track': sum(1 for p in performance if p['achievement_percentage'] <= 100),
            'budgets_over': sum(1 for p in performance if p['achievement_percentage'] > 100)
        }
    }), 200
