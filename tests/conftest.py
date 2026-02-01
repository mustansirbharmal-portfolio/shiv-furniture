import pytest
from app import create_app
from app.config import TestConfig
from app.database import get_db

@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    with app.app_context():
        database = get_db()
        yield database
        database.users.delete_many({})
        database.contacts.delete_many({})
        database.products.delete_many({})
        database.analytical_accounts.delete_many({})
        database.budgets.delete_many({})
        database.auto_analytical_models.delete_many({})
        database.purchase_orders.delete_many({})
        database.vendor_bills.delete_many({})
        database.sales_orders.delete_many({})
        database.customer_invoices.delete_many({})
        database.payments.delete_many({})
        database.counters.delete_many({})

@pytest.fixture
def auth_headers(client, db):
    response = client.post('/api/auth/register', json={
        'email': 'admin@test.com',
        'password': 'Test@123456',
        'full_name': 'Test Admin'
    })
    data = response.get_json()
    
    db.users.update_one(
        {'email': 'admin@test.com'},
        {'$set': {'role': 'admin'}}
    )
    
    login_response = client.post('/api/auth/login', json={
        'email': 'admin@test.com',
        'password': 'Test@123456'
    })
    login_data = login_response.get_json()
    
    return {'Authorization': f"Bearer {login_data['access_token']}"}

@pytest.fixture
def portal_user_headers(client, db):
    response = client.post('/api/auth/register', json={
        'email': 'portal@test.com',
        'password': 'Test@123456',
        'full_name': 'Portal User'
    })
    data = response.get_json()
    
    return {'Authorization': f"Bearer {data['access_token']}"}
