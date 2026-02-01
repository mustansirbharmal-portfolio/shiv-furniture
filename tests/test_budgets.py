import pytest
from datetime import datetime, timedelta

class TestBudgets:
    def create_analytical_account(self, client, auth_headers):
        response = client.post('/api/analytical-accounts',
            headers=auth_headers,
            json={
                'code': 'ACC001',
                'name': 'Test Account',
                'account_type': 'expense'
            }
        )
        return response.get_json()['analytical_account']['_id']
    
    def test_create_budget(self, client, db, auth_headers):
        account_id = self.create_analytical_account(client, auth_headers)
        
        response = client.post('/api/budgets',
            headers=auth_headers,
            json={
                'name': 'Q1 Marketing Budget',
                'analytical_account_id': account_id,
                'budget_type': 'expense',
                'period_start': '2026-01-01',
                'period_end': '2026-03-31',
                'budgeted_amount': 100000
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['budget']['name'] == 'Q1 Marketing Budget'
        assert data['budget']['budgeted_amount'] == 100000
    
    def test_create_budget_invalid_period(self, client, db, auth_headers):
        account_id = self.create_analytical_account(client, auth_headers)
        
        response = client.post('/api/budgets',
            headers=auth_headers,
            json={
                'name': 'Invalid Budget',
                'analytical_account_id': account_id,
                'budget_type': 'expense',
                'period_start': '2026-03-31',
                'period_end': '2026-01-01',
                'budgeted_amount': 100000
            }
        )
        
        assert response.status_code == 400
    
    def test_get_budgets(self, client, db, auth_headers):
        account_id = self.create_analytical_account(client, auth_headers)
        
        client.post('/api/budgets', headers=auth_headers, json={
            'name': 'Budget 1',
            'analytical_account_id': account_id,
            'budget_type': 'expense',
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'budgeted_amount': 50000
        })
        client.post('/api/budgets', headers=auth_headers, json={
            'name': 'Budget 2',
            'analytical_account_id': account_id,
            'budget_type': 'income',
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'budgeted_amount': 100000
        })
        
        response = client.get('/api/budgets', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] == 2
    
    def test_update_budget_with_revision(self, client, db, auth_headers):
        account_id = self.create_analytical_account(client, auth_headers)
        
        create_response = client.post('/api/budgets', headers=auth_headers, json={
            'name': 'Original Budget',
            'analytical_account_id': account_id,
            'budget_type': 'expense',
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'budgeted_amount': 50000
        })
        budget_id = create_response.get_json()['budget']['_id']
        
        response = client.put(f'/api/budgets/{budget_id}',
            headers=auth_headers,
            json={
                'budgeted_amount': 75000,
                'revision_reason': 'Increased marketing spend'
            }
        )
        
        assert response.status_code == 200
        assert response.get_json()['budget']['budgeted_amount'] == 75000
        
        get_response = client.get(f'/api/budgets/{budget_id}', headers=auth_headers)
        data = get_response.get_json()
        assert len(data['revisions']) == 1
        assert data['revisions'][0]['previous_amount'] == 50000
        assert data['revisions'][0]['new_amount'] == 75000
    
    def test_get_budget_performance(self, client, db, auth_headers):
        account_id = self.create_analytical_account(client, auth_headers)
        
        create_response = client.post('/api/budgets', headers=auth_headers, json={
            'name': 'Performance Budget',
            'analytical_account_id': account_id,
            'budget_type': 'expense',
            'period_start': '2026-01-01',
            'period_end': '2026-12-31',
            'budgeted_amount': 100000
        })
        budget_id = create_response.get_json()['budget']['_id']
        
        response = client.get(f'/api/budgets/{budget_id}/performance', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'budgeted_amount' in data
        assert 'actual_amount' in data
        assert 'achievement_percentage' in data
    
    def test_archive_budget(self, client, db, auth_headers):
        account_id = self.create_analytical_account(client, auth_headers)
        
        create_response = client.post('/api/budgets', headers=auth_headers, json={
            'name': 'To Archive',
            'analytical_account_id': account_id,
            'budget_type': 'expense',
            'period_start': '2026-01-01',
            'period_end': '2026-03-31',
            'budgeted_amount': 50000
        })
        budget_id = create_response.get_json()['budget']['_id']
        
        response = client.post(f'/api/budgets/{budget_id}/archive', headers=auth_headers)
        
        assert response.status_code == 200
        assert response.get_json()['is_archived'] == True
