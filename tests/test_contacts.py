import pytest

class TestContacts:
    def test_create_contact(self, client, db, auth_headers):
        response = client.post('/api/contacts', 
            headers=auth_headers,
            json={
                'name': 'Test Customer',
                'email': 'customer@test.com',
                'phone': '9876543210',
                'contact_type': 'customer',
                'company_name': 'Test Company'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['contact']['name'] == 'Test Customer'
        assert data['contact']['contact_type'] == 'customer'
    
    def test_create_contact_missing_name(self, client, db, auth_headers):
        response = client.post('/api/contacts',
            headers=auth_headers,
            json={
                'email': 'noname@test.com'
            }
        )
        
        assert response.status_code == 400
    
    def test_get_contacts(self, client, db, auth_headers):
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Customer 1',
            'contact_type': 'customer'
        })
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Vendor 1',
            'contact_type': 'vendor'
        })
        
        response = client.get('/api/contacts', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 2
    
    def test_get_contacts_by_type(self, client, db, auth_headers):
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Customer 1',
            'contact_type': 'customer'
        })
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Vendor 1',
            'contact_type': 'vendor'
        })
        
        response = client.get('/api/contacts?type=customer', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
        assert data['contacts'][0]['contact_type'] == 'customer'
    
    def test_update_contact(self, client, db, auth_headers):
        create_response = client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Original Name',
            'contact_type': 'customer'
        })
        contact_id = create_response.get_json()['contact']['_id']
        
        response = client.put(f'/api/contacts/{contact_id}',
            headers=auth_headers,
            json={'name': 'Updated Name'}
        )
        
        assert response.status_code == 200
        assert response.get_json()['contact']['name'] == 'Updated Name'
    
    def test_archive_contact(self, client, db, auth_headers):
        create_response = client.post('/api/contacts', headers=auth_headers, json={
            'name': 'To Archive',
            'contact_type': 'customer'
        })
        contact_id = create_response.get_json()['contact']['_id']
        
        response = client.post(f'/api/contacts/{contact_id}/archive', headers=auth_headers)
        
        assert response.status_code == 200
        assert response.get_json()['is_archived'] == True
    
    def test_get_customers_endpoint(self, client, db, auth_headers):
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Customer',
            'contact_type': 'customer'
        })
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Vendor',
            'contact_type': 'vendor'
        })
        
        response = client.get('/api/contacts/customers', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['customers']) == 1
    
    def test_get_vendors_endpoint(self, client, db, auth_headers):
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Customer',
            'contact_type': 'customer'
        })
        client.post('/api/contacts', headers=auth_headers, json={
            'name': 'Vendor',
            'contact_type': 'vendor'
        })
        
        response = client.get('/api/contacts/vendors', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['vendors']) == 1
