import razorpay
import os
from datetime import datetime

class RazorpayService:
    _client = None
    
    @classmethod
    def get_client(cls):
        if cls._client is None:
            key_id = os.getenv('RAZORPAY_KEY_ID')
            key_secret = os.getenv('RAZORPAY_KEY_SECRET')
            if key_id and key_secret:
                cls._client = razorpay.Client(auth=(key_id, key_secret))
        return cls._client
    
    @classmethod
    def create_order(cls, amount, currency='INR', receipt=None, notes=None):
        """
        Create a Razorpay order
        amount: Amount in paise (e.g., 10000 for Rs. 100)
        """
        client = cls.get_client()
        if not client:
            raise Exception("Razorpay not configured")
        
        order_data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': currency,
            'receipt': receipt or f'receipt_{datetime.utcnow().timestamp()}',
            'notes': notes or {}
        }
        
        order = client.order.create(data=order_data)
        return order
    
    @classmethod
    def verify_payment(cls, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify payment signature
        """
        client = cls.get_client()
        if not client:
            raise Exception("Razorpay not configured")
        
        params = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            client.utility.verify_payment_signature(params)
            return True
        except razorpay.errors.SignatureVerificationError:
            return False
    
    @classmethod
    def get_payment(cls, payment_id):
        """
        Get payment details
        """
        client = cls.get_client()
        if not client:
            raise Exception("Razorpay not configured")
        
        return client.payment.fetch(payment_id)
    
    @classmethod
    def get_key_id(cls):
        """
        Get the Razorpay key ID for frontend
        """
        return os.getenv('RAZORPAY_KEY_ID')
