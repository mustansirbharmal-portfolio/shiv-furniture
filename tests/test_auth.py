import pytest

class TestAuth:
    def test_register_success(self, client, db):
        response = client.post('/api/auth/register', json={
            'email': 'newuser@test.com',
            'password': 'Test@123456',
            'full_name': 'New User'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'newuser@test.com'
    
    def test_register_duplicate_email(self, client, db):
        client.post('/api/auth/register', json={
            'email': 'duplicate@test.com',
            'password': 'Test@123456',
            'full_name': 'User 1'
        })
        
        response = client.post('/api/auth/register', json={
            'email': 'duplicate@test.com',
            'password': 'Test@123456',
            'full_name': 'User 2'
        })
        
        assert response.status_code == 400
        assert 'already registered' in response.get_json()['error']
    
    def test_register_missing_fields(self, client, db):
        response = client.post('/api/auth/register', json={
            'email': 'test@test.com'
        })
        
        assert response.status_code == 400
    
    def test_login_success(self, client, db):
        client.post('/api/auth/register', json={
            'email': 'login@test.com',
            'password': 'Test@123456',
            'full_name': 'Login User'
        })
        
        response = client.post('/api/auth/login', json={
            'email': 'login@test.com',
            'password': 'Test@123456'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
    
    def test_login_wrong_password(self, client, db):
        client.post('/api/auth/register', json={
            'email': 'wrongpass@test.com',
            'password': 'Test@123456',
            'full_name': 'Wrong Pass User'
        })
        
        response = client.post('/api/auth/login', json={
            'email': 'wrongpass@test.com',
            'password': 'WrongPassword'
        })
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client, db):
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@test.com',
            'password': 'Test@123456'
        })
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client, db, auth_headers):
        response = client.get('/api/auth/me', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['email'] == 'admin@test.com'
    
    def test_change_password(self, client, db):
        client.post('/api/auth/register', json={
            'email': 'changepass@test.com',
            'password': 'OldPass@123',
            'full_name': 'Change Pass User'
        })
        
        login_response = client.post('/api/auth/login', json={
            'email': 'changepass@test.com',
            'password': 'OldPass@123'
        })
        token = login_response.get_json()['access_token']
        
        response = client.post('/api/auth/change-password', 
            headers={'Authorization': f'Bearer {token}'},
            json={
                'current_password': 'OldPass@123',
                'new_password': 'NewPass@123'
            }
        )
        
        assert response.status_code == 200
        
        new_login = client.post('/api/auth/login', json={
            'email': 'changepass@test.com',
            'password': 'NewPass@123'
        })
        assert new_login.status_code == 200
