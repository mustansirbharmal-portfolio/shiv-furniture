from datetime import datetime
from bson import ObjectId
from app.database import get_db

class AnalyticsService:
    @staticmethod
    def get_analytical_account_for_transaction(product_id=None, category=None, contact_id=None, amount=None):
        db = get_db()
        
        models = list(db.auto_analytical_models.find({'is_active': True}).sort('priority', -1))
        
        for model in models:
            rule_type = model.get('rule_type')
            rule_value = model.get('rule_value')
            
            if rule_type == 'product' and product_id:
                if str(product_id) == str(rule_value):
                    return model.get('analytical_account_id')
            
            elif rule_type == 'product_category' and category:
                if category.lower() == str(rule_value).lower():
                    return model.get('analytical_account_id')
            
            elif rule_type == 'contact' and contact_id:
                if str(contact_id) == str(rule_value):
                    return model.get('analytical_account_id')
            
            elif rule_type == 'amount_range' and amount is not None:
                try:
                    range_parts = str(rule_value).split('-')
                    min_amount = float(range_parts[0])
                    max_amount = float(range_parts[1]) if len(range_parts) > 1 else float('inf')
                    if min_amount <= amount <= max_amount:
                        return model.get('analytical_account_id')
                except (ValueError, IndexError):
                    continue
        
        if product_id:
            product = db.products.find_one({'_id': ObjectId(product_id)})
            if product and product.get('default_analytical_account_id'):
                return product.get('default_analytical_account_id')
        
        return None
    
    @staticmethod
    def calculate_budget_actuals(budget_id, period_start=None, period_end=None):
        db = get_db()
        
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        if not budget:
            return None
        
        analytical_account_id = budget.get('analytical_account_id')
        budget_type = budget.get('budget_type')
        start_date = period_start or budget.get('period_start')
        end_date = period_end or budget.get('period_end')
        
        actual_amount = 0
        
        if budget_type == 'expense':
            bills = db.vendor_bills.find({
                'analytical_account_id': analytical_account_id,
                'status': 'posted',
                'bill_date': {'$gte': start_date, '$lte': end_date}
            })
            actual_amount = sum(bill.get('total_amount', 0) for bill in bills)
        
        elif budget_type == 'income':
            invoices = db.customer_invoices.find({
                'analytical_account_id': analytical_account_id,
                'status': 'posted',
                'invoice_date': {'$gte': start_date, '$lte': end_date}
            })
            actual_amount = sum(inv.get('total_amount', 0) for inv in invoices)
        
        budgeted_amount = budget.get('budgeted_amount', 0)
        
        if budgeted_amount > 0:
            achievement_percentage = (actual_amount / budgeted_amount) * 100
        else:
            achievement_percentage = 0
        
        remaining_balance = budgeted_amount - actual_amount
        
        return {
            'budget_id': str(budget_id),
            'budget_name': budget.get('name'),
            'budget_type': budget_type,
            'analytical_account_id': str(analytical_account_id) if analytical_account_id else None,
            'period_start': start_date.isoformat() if start_date else None,
            'period_end': end_date.isoformat() if end_date else None,
            'budgeted_amount': budgeted_amount,
            'actual_amount': actual_amount,
            'remaining_balance': remaining_balance,
            'achievement_percentage': round(achievement_percentage, 2),
            'variance': budgeted_amount - actual_amount
        }
    
    @staticmethod
    def get_all_budgets_performance(period_start=None, period_end=None):
        db = get_db()
        
        query = {'is_archived': False}
        if period_start and period_end:
            query['$or'] = [
                {'period_start': {'$lte': period_end}, 'period_end': {'$gte': period_start}},
            ]
        
        budgets = list(db.budgets.find(query))
        
        results = []
        for budget in budgets:
            performance = AnalyticsService.calculate_budget_actuals(
                budget['_id'],
                period_start,
                period_end
            )
            if performance:
                account = db.analytical_accounts.find_one({'_id': budget.get('analytical_account_id')})
                performance['analytical_account_name'] = account.get('name') if account else None
                performance['analytical_account_code'] = account.get('code') if account else None
                results.append(performance)
        
        return results
    
    @staticmethod
    def get_dashboard_summary():
        db = get_db()
        
        current_date = datetime.utcnow()
        start_of_month = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total_customers = db.contacts.count_documents({'contact_type': {'$in': ['customer', 'both']}, 'is_archived': False})
        total_vendors = db.contacts.count_documents({'contact_type': {'$in': ['vendor', 'both']}, 'is_archived': False})
        total_products = db.products.count_documents({'is_archived': False})
        
        pending_invoices = db.customer_invoices.count_documents({'payment_status': {'$ne': 'paid'}, 'status': 'posted'})
        pending_bills = db.vendor_bills.count_documents({'payment_status': {'$ne': 'paid'}, 'status': 'posted'})
        
        invoices_pipeline = [
            {'$match': {'status': 'posted', 'invoice_date': {'$gte': start_of_month}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
        ]
        invoices_result = list(db.customer_invoices.aggregate(invoices_pipeline))
        total_sales_this_month = invoices_result[0]['total'] if invoices_result else 0
        
        bills_pipeline = [
            {'$match': {'status': 'posted', 'bill_date': {'$gte': start_of_month}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
        ]
        bills_result = list(db.vendor_bills.aggregate(bills_pipeline))
        total_purchases_this_month = bills_result[0]['total'] if bills_result else 0
        
        receivable_pipeline = [
            {'$match': {'payment_status': {'$ne': 'paid'}, 'status': 'posted'}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount_due'}}}
        ]
        receivable_result = list(db.customer_invoices.aggregate(receivable_pipeline))
        total_receivable = receivable_result[0]['total'] if receivable_result else 0
        
        payable_pipeline = [
            {'$match': {'payment_status': {'$ne': 'paid'}, 'status': 'posted'}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount_due'}}}
        ]
        payable_result = list(db.vendor_bills.aggregate(payable_pipeline))
        total_payable = payable_result[0]['total'] if payable_result else 0
        
        budgets_performance = AnalyticsService.get_all_budgets_performance()
        budgets_on_track = sum(1 for b in budgets_performance if b['achievement_percentage'] <= 100)
        budgets_over = sum(1 for b in budgets_performance if b['achievement_percentage'] > 100)
        
        return {
            'total_customers': total_customers,
            'total_vendors': total_vendors,
            'total_products': total_products,
            'pending_invoices': pending_invoices,
            'pending_bills': pending_bills,
            'total_sales_this_month': total_sales_this_month,
            'total_purchases_this_month': total_purchases_this_month,
            'total_receivable': total_receivable,
            'total_payable': total_payable,
            'budgets_on_track': budgets_on_track,
            'budgets_over': budgets_over,
            'net_position': total_receivable - total_payable
        }
    
    @staticmethod
    def get_monthly_trends(year=None):
        db = get_db()
        
        if not year:
            year = datetime.utcnow().year
        
        monthly_data = []
        
        for month in range(1, 13):
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            
            sales_pipeline = [
                {'$match': {'status': 'posted', 'invoice_date': {'$gte': start_date, '$lt': end_date}}},
                {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
            ]
            sales_result = list(db.customer_invoices.aggregate(sales_pipeline))
            sales = sales_result[0]['total'] if sales_result else 0
            
            purchases_pipeline = [
                {'$match': {'status': 'posted', 'bill_date': {'$gte': start_date, '$lt': end_date}}},
                {'$group': {'_id': None, 'total': {'$sum': '$total_amount'}}}
            ]
            purchases_result = list(db.vendor_bills.aggregate(purchases_pipeline))
            purchases = purchases_result[0]['total'] if purchases_result else 0
            
            monthly_data.append({
                'month': month,
                'month_name': start_date.strftime('%B'),
                'sales': sales,
                'purchases': purchases,
                'profit': sales - purchases
            })
        
        return monthly_data
