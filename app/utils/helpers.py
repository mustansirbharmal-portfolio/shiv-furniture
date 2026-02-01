from datetime import datetime
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.database import get_db

def generate_number(prefix, collection_name):
    db = get_db()
    
    year = datetime.utcnow().strftime('%Y')
    month = datetime.utcnow().strftime('%m')
    
    counter_id = f"{collection_name}_{year}_{month}"
    
    counter = db.counters.find_one_and_update(
        {'_id': counter_id},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=True
    )
    
    seq = counter['seq']
    return f"{prefix}-{year}{month}-{seq:04d}"

def parse_date(date_string):
    if not date_string:
        return None
    
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%d/%m/%Y',
        '%d-%m-%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None

def get_current_user_id():
    try:
        verify_jwt_in_request()
        return get_jwt_identity()
    except:
        return None

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        db = get_db()
        from bson import ObjectId
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper
