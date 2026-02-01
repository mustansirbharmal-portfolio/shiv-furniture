from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
from bson import ObjectId

from app.database import get_db
from app.utils.helpers import parse_date
from app.services.analytics_service import AnalyticsService

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    summary = AnalyticsService.get_dashboard_summary()
    return jsonify(summary), 200

@reports_bp.route('/budget-performance', methods=['GET'])
@jwt_required()
def get_budget_performance():
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    start_date = parse_date(period_start) if period_start else None
    end_date = parse_date(period_end) if period_end else None
    
    performance = AnalyticsService.get_all_budgets_performance(start_date, end_date)
    
    return jsonify({
        'budgets': performance,
        'summary': {
            'total_budgeted': sum(p['budgeted_amount'] for p in performance),
            'total_actual': sum(p['actual_amount'] for p in performance),
            'total_remaining': sum(p['remaining_balance'] for p in performance),
            'budgets_on_track': sum(1 for p in performance if p['achievement_percentage'] <= 100),
            'budgets_over': sum(1 for p in performance if p['achievement_percentage'] > 100)
        }
    }), 200

@reports_bp.route('/monthly-trends', methods=['GET'])
@jwt_required()
def get_monthly_trends():
    year = request.args.get('year', type=int)
    trends = AnalyticsService.get_monthly_trends(year)
    return jsonify({'trends': trends}), 200

@reports_bp.route('/sales-summary', methods=['GET'])
@jwt_required()
def get_sales_summary():
    db = get_db()
    
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    start_date = parse_date(period_start) if period_start else datetime(datetime.utcnow().year, 1, 1)
    end_date = parse_date(period_end) if period_end else datetime.utcnow()
    
    pipeline = [
        {'$match': {
            'status': 'posted',
            'invoice_date': {'$gte': start_date, '$lte': end_date}
        }},
        {'$group': {
            '_id': None,
            'total_invoices': {'$sum': 1},
            'total_amount': {'$sum': '$total_amount'},
            'total_paid': {'$sum': '$amount_paid'},
            'total_due': {'$sum': '$amount_due'}
        }}
    ]
    
    result = list(db.customer_invoices.aggregate(pipeline))
    summary = result[0] if result else {
        'total_invoices': 0,
        'total_amount': 0,
        'total_paid': 0,
        'total_due': 0
    }
    
    by_customer_pipeline = [
        {'$match': {
            'status': 'posted',
            'invoice_date': {'$gte': start_date, '$lte': end_date}
        }},
        {'$group': {
            '_id': '$customer_id',
            'total_amount': {'$sum': '$total_amount'},
            'invoice_count': {'$sum': 1}
        }},
        {'$sort': {'total_amount': -1}},
        {'$limit': 10}
    ]
    
    by_customer = list(db.customer_invoices.aggregate(by_customer_pipeline))
    
    for item in by_customer:
        if item['_id']:
            customer = db.contacts.find_one({'_id': item['_id']})
            item['customer_name'] = customer.get('name') if customer else 'Unknown'
            item['_id'] = str(item['_id'])
    
    return jsonify({
        'summary': summary,
        'top_customers': by_customer,
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }), 200

@reports_bp.route('/purchase-summary', methods=['GET'])
@jwt_required()
def get_purchase_summary():
    db = get_db()
    
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    start_date = parse_date(period_start) if period_start else datetime(datetime.utcnow().year, 1, 1)
    end_date = parse_date(period_end) if period_end else datetime.utcnow()
    
    pipeline = [
        {'$match': {
            'status': 'posted',
            'bill_date': {'$gte': start_date, '$lte': end_date}
        }},
        {'$group': {
            '_id': None,
            'total_bills': {'$sum': 1},
            'total_amount': {'$sum': '$total_amount'},
            'total_paid': {'$sum': '$amount_paid'},
            'total_due': {'$sum': '$amount_due'}
        }}
    ]
    
    result = list(db.vendor_bills.aggregate(pipeline))
    summary = result[0] if result else {
        'total_bills': 0,
        'total_amount': 0,
        'total_paid': 0,
        'total_due': 0
    }
    
    by_vendor_pipeline = [
        {'$match': {
            'status': 'posted',
            'bill_date': {'$gte': start_date, '$lte': end_date}
        }},
        {'$group': {
            '_id': '$vendor_id',
            'total_amount': {'$sum': '$total_amount'},
            'bill_count': {'$sum': 1}
        }},
        {'$sort': {'total_amount': -1}},
        {'$limit': 10}
    ]
    
    by_vendor = list(db.vendor_bills.aggregate(by_vendor_pipeline))
    
    for item in by_vendor:
        if item['_id']:
            vendor = db.contacts.find_one({'_id': item['_id']})
            item['vendor_name'] = vendor.get('name') if vendor else 'Unknown'
            item['_id'] = str(item['_id'])
    
    return jsonify({
        'summary': summary,
        'top_vendors': by_vendor,
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }), 200

@reports_bp.route('/analytical-account-summary', methods=['GET'])
@jwt_required()
def get_analytical_account_summary():
    db = get_db()
    
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    
    start_date = parse_date(period_start) if period_start else datetime(datetime.utcnow().year, 1, 1)
    end_date = parse_date(period_end) if period_end else datetime.utcnow()
    
    expense_pipeline = [
        {'$match': {
            'status': 'posted',
            'bill_date': {'$gte': start_date, '$lte': end_date},
            'analytical_account_id': {'$ne': None}
        }},
        {'$group': {
            '_id': '$analytical_account_id',
            'total_expense': {'$sum': '$total_amount'}
        }}
    ]
    
    expenses = {str(e['_id']): e['total_expense'] for e in db.vendor_bills.aggregate(expense_pipeline)}
    
    income_pipeline = [
        {'$match': {
            'status': 'posted',
            'invoice_date': {'$gte': start_date, '$lte': end_date},
            'analytical_account_id': {'$ne': None}
        }},
        {'$group': {
            '_id': '$analytical_account_id',
            'total_income': {'$sum': '$total_amount'}
        }}
    ]
    
    incomes = {str(i['_id']): i['total_income'] for i in db.customer_invoices.aggregate(income_pipeline)}
    
    accounts = list(db.analytical_accounts.find({'is_archived': False}))
    
    summary = []
    for account in accounts:
        account_id = str(account['_id'])
        expense = expenses.get(account_id, 0)
        income = incomes.get(account_id, 0)
        
        summary.append({
            '_id': account_id,
            'code': account.get('code'),
            'name': account.get('name'),
            'account_type': account.get('account_type'),
            'total_expense': expense,
            'total_income': income,
            'net': income - expense
        })
    
    summary.sort(key=lambda x: abs(x['net']), reverse=True)
    
    return jsonify({
        'accounts': summary,
        'totals': {
            'total_expense': sum(a['total_expense'] for a in summary),
            'total_income': sum(a['total_income'] for a in summary),
            'net': sum(a['net'] for a in summary)
        },
        'period': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }), 200

@reports_bp.route('/receivables-aging', methods=['GET'])
@jwt_required()
def get_receivables_aging():
    db = get_db()
    
    today = datetime.utcnow()
    
    invoices = list(db.customer_invoices.find({
        'status': 'posted',
        'payment_status': {'$ne': 'paid'}
    }))
    
    aging = {
        'current': {'count': 0, 'amount': 0},
        '1_30': {'count': 0, 'amount': 0},
        '31_60': {'count': 0, 'amount': 0},
        '61_90': {'count': 0, 'amount': 0},
        'over_90': {'count': 0, 'amount': 0}
    }
    
    details = []
    
    for invoice in invoices:
        due_date = invoice.get('due_date')
        if not due_date:
            continue
        
        days_overdue = (today - due_date).days
        amount_due = invoice.get('amount_due', 0)
        
        customer = db.contacts.find_one({'_id': invoice.get('customer_id')})
        
        detail = {
            'invoice_number': invoice.get('invoice_number'),
            'customer_name': customer.get('name') if customer else 'Unknown',
            'due_date': due_date.isoformat(),
            'amount_due': amount_due,
            'days_overdue': max(0, days_overdue)
        }
        details.append(detail)
        
        if days_overdue <= 0:
            aging['current']['count'] += 1
            aging['current']['amount'] += amount_due
        elif days_overdue <= 30:
            aging['1_30']['count'] += 1
            aging['1_30']['amount'] += amount_due
        elif days_overdue <= 60:
            aging['31_60']['count'] += 1
            aging['31_60']['amount'] += amount_due
        elif days_overdue <= 90:
            aging['61_90']['count'] += 1
            aging['61_90']['amount'] += amount_due
        else:
            aging['over_90']['count'] += 1
            aging['over_90']['amount'] += amount_due
    
    details.sort(key=lambda x: x['days_overdue'], reverse=True)
    
    return jsonify({
        'aging': aging,
        'details': details[:50],
        'total_receivable': sum(a['amount'] for a in aging.values())
    }), 200

@reports_bp.route('/payables-aging', methods=['GET'])
@jwt_required()
def get_payables_aging():
    db = get_db()
    
    today = datetime.utcnow()
    
    bills = list(db.vendor_bills.find({
        'status': 'posted',
        'payment_status': {'$ne': 'paid'}
    }))
    
    aging = {
        'current': {'count': 0, 'amount': 0},
        '1_30': {'count': 0, 'amount': 0},
        '31_60': {'count': 0, 'amount': 0},
        '61_90': {'count': 0, 'amount': 0},
        'over_90': {'count': 0, 'amount': 0}
    }
    
    details = []
    
    for bill in bills:
        due_date = bill.get('due_date')
        if not due_date:
            continue
        
        days_overdue = (today - due_date).days
        amount_due = bill.get('amount_due', 0)
        
        vendor = db.contacts.find_one({'_id': bill.get('vendor_id')})
        
        detail = {
            'bill_number': bill.get('bill_number'),
            'vendor_name': vendor.get('name') if vendor else 'Unknown',
            'due_date': due_date.isoformat(),
            'amount_due': amount_due,
            'days_overdue': max(0, days_overdue)
        }
        details.append(detail)
        
        if days_overdue <= 0:
            aging['current']['count'] += 1
            aging['current']['amount'] += amount_due
        elif days_overdue <= 30:
            aging['1_30']['count'] += 1
            aging['1_30']['amount'] += amount_due
        elif days_overdue <= 60:
            aging['31_60']['count'] += 1
            aging['31_60']['amount'] += amount_due
        elif days_overdue <= 90:
            aging['61_90']['count'] += 1
            aging['61_90']['amount'] += amount_due
        else:
            aging['over_90']['count'] += 1
            aging['over_90']['amount'] += amount_due
    
    details.sort(key=lambda x: x['days_overdue'], reverse=True)
    
    return jsonify({
        'aging': aging,
        'details': details[:50],
        'total_payable': sum(a['amount'] for a in aging.values())
    }), 200
