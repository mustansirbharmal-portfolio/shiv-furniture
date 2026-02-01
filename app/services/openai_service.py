"""
Azure OpenAI Service for AI-powered features
"""
import os
import requests
import json

class OpenAIService:
    
    @staticmethod
    def get_config():
        """Get Azure OpenAI configuration from environment"""
        return {
            'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
            'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
            'deployment': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o-mini'),
            'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
        }
    
    @staticmethod
    def is_configured():
        """Check if Azure OpenAI is configured"""
        config = OpenAIService.get_config()
        return bool(config['endpoint'] and config['api_key'])
    
    @staticmethod
    def generate_rule_value(model_name, rule_type):
        """
        Generate a rule value suggestion based on model name and rule type
        """
        if not OpenAIService.is_configured():
            return None
        
        config = OpenAIService.get_config()
        
        rule_type_descriptions = {
            'product_category': 'a product category name (e.g., Electronics, Furniture, Office Supplies)',
            'product': 'a specific product name or ID',
            'contact': 'a contact/vendor/customer name or type',
            'amount_range': 'an amount range in format min-max (e.g., 1000-5000)'
        }
        
        rule_desc = rule_type_descriptions.get(rule_type, 'a matching value')
        
        prompt = f"""Based on the analytical model name "{model_name}", suggest an appropriate rule value.
The rule type is "{rule_type}" which should be {rule_desc}.

For example:
- If name is "Marketing Expenses" and type is "product_category", suggest "Marketing"
- If name is "Office Supplies Cost" and type is "product_category", suggest "Office Supplies"
- If name is "High Value Transactions" and type is "amount_range", suggest "50000-100000"
- If name is "Vendor ABC Purchases" and type is "contact", suggest "ABC Enterprises"

Respond with ONLY the suggested rule value, nothing else. Keep it short and relevant."""

        try:
            url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': config['api_key']
            }
            
            payload = {
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful assistant that suggests rule values for accounting analytical models. Respond with only the suggested value, no explanations.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 50,
                'temperature': 0.7
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                suggestion = result['choices'][0]['message']['content'].strip()
                # Clean up the suggestion (remove quotes if present)
                suggestion = suggestion.strip('"\'')
                return suggestion
            else:
                print(f"Azure OpenAI error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return None
    
    @staticmethod
    def analyze_transaction(description, amount, contact_name=None):
        """
        Analyze a transaction and suggest an analytical account
        """
        if not OpenAIService.is_configured():
            return None
        
        config = OpenAIService.get_config()
        
        prompt = f"""Analyze this transaction and suggest an appropriate cost center/analytical account category:
Description: {description}
Amount: ₹{amount:,.2f}
{f'Contact: {contact_name}' if contact_name else ''}

Suggest a category from: Marketing, Sales, Operations, Administration, IT, HR, Finance, Logistics, Production, Maintenance, R&D, Customer Service

Respond with ONLY the category name."""

        try:
            url = f"{config['endpoint']}/openai/deployments/{config['deployment']}/chat/completions?api-version={config['api_version']}"
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': config['api_key']
            }
            
            payload = {
                'messages': [
                    {'role': 'system', 'content': 'You are an accounting assistant that categorizes transactions. Respond with only the category name.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 20,
                'temperature': 0.3
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return None
                
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return None
