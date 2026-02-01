from app.routes.auth import auth_bp
from app.routes.users import users_bp
from app.routes.contacts import contacts_bp
from app.routes.products import products_bp
from app.routes.analytical_accounts import analytical_accounts_bp
from app.routes.budgets import budgets_bp
from app.routes.auto_analytical_models import auto_analytical_models_bp
from app.routes.purchase_orders import purchase_orders_bp
from app.routes.vendor_bills import vendor_bills_bp
from app.routes.sales_orders import sales_orders_bp
from app.routes.customer_invoices import customer_invoices_bp
from app.routes.payments import payments_bp
from app.routes.reports import reports_bp
from app.routes.portal import portal_bp
from app.routes.files import files_bp
from app.routes.notifications import notifications_bp

def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(contacts_bp, url_prefix='/api/contacts')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(analytical_accounts_bp, url_prefix='/api/analytical-accounts')
    app.register_blueprint(budgets_bp, url_prefix='/api/budgets')
    app.register_blueprint(auto_analytical_models_bp, url_prefix='/api/auto-analytical-models')
    app.register_blueprint(purchase_orders_bp, url_prefix='/api/purchase-orders')
    app.register_blueprint(vendor_bills_bp, url_prefix='/api/vendor-bills')
    app.register_blueprint(sales_orders_bp, url_prefix='/api/sales-orders')
    app.register_blueprint(customer_invoices_bp, url_prefix='/api/customer-invoices')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    app.register_blueprint(portal_bp, url_prefix='/api/portal')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
