import pytest

class TestProducts:
    def test_create_product(self, client, db, auth_headers):
        response = client.post('/api/products',
            headers=auth_headers,
            json={
                'name': 'Wooden Chair',
                'sku': 'WC001',
                'category': 'Furniture',
                'purchase_price': 500,
                'sale_price': 800,
                'tax_rate': 18
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['product']['name'] == 'Wooden Chair'
        assert data['product']['sku'] == 'WC001'
    
    def test_create_product_duplicate_sku(self, client, db, auth_headers):
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Product 1',
            'sku': 'DUP001'
        })
        
        response = client.post('/api/products', headers=auth_headers, json={
            'name': 'Product 2',
            'sku': 'DUP001'
        })
        
        assert response.status_code == 400
        assert 'already exists' in response.get_json()['error']
    
    def test_get_products(self, client, db, auth_headers):
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Product 1',
            'sku': 'P001'
        })
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Product 2',
            'sku': 'P002'
        })
        
        response = client.get('/api/products', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 2
    
    def test_get_products_by_category(self, client, db, auth_headers):
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Chair',
            'sku': 'CH001',
            'category': 'Furniture'
        })
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Hammer',
            'sku': 'HM001',
            'category': 'Tools'
        })
        
        response = client.get('/api/products?category=Furniture', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 1
    
    def test_update_product(self, client, db, auth_headers):
        create_response = client.post('/api/products', headers=auth_headers, json={
            'name': 'Original Product',
            'sku': 'OP001',
            'sale_price': 100
        })
        product_id = create_response.get_json()['product']['_id']
        
        response = client.put(f'/api/products/{product_id}',
            headers=auth_headers,
            json={'sale_price': 150}
        )
        
        assert response.status_code == 200
        assert response.get_json()['product']['sale_price'] == 150
    
    def test_archive_product(self, client, db, auth_headers):
        create_response = client.post('/api/products', headers=auth_headers, json={
            'name': 'To Archive',
            'sku': 'TA001'
        })
        product_id = create_response.get_json()['product']['_id']
        
        response = client.post(f'/api/products/{product_id}/archive', headers=auth_headers)
        
        assert response.status_code == 200
        assert response.get_json()['is_archived'] == True
    
    def test_get_categories(self, client, db, auth_headers):
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Chair',
            'sku': 'CH001',
            'category': 'Furniture'
        })
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Table',
            'sku': 'TB001',
            'category': 'Furniture'
        })
        client.post('/api/products', headers=auth_headers, json={
            'name': 'Hammer',
            'sku': 'HM001',
            'category': 'Tools'
        })
        
        response = client.get('/api/products/categories', headers=auth_headers)
        
        assert response.status_code == 200
        categories = response.get_json()['categories']
        assert 'Furniture' in categories
        assert 'Tools' in categories
