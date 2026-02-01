from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.notification_service import NotificationService

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get notifications for the current user"""
    user_id = get_jwt_identity()
    
    limit = int(request.args.get('limit', 20))
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    notifications = NotificationService.get_user_notifications(user_id, limit, unread_only)
    unread_count = NotificationService.get_unread_count(user_id)
    
    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    }), 200

@notifications_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Get count of unread notifications"""
    user_id = get_jwt_identity()
    count = NotificationService.get_unread_count(user_id)
    
    return jsonify({'unread_count': count}), 200

@notifications_bp.route('/<notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    user_id = get_jwt_identity()
    
    success = NotificationService.mark_as_read(notification_id, user_id)
    
    if success:
        return jsonify({'message': 'Notification marked as read'}), 200
    return jsonify({'error': 'Notification not found'}), 404

@notifications_bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_read():
    """Mark all notifications as read"""
    user_id = get_jwt_identity()
    
    count = NotificationService.mark_all_as_read(user_id)
    
    return jsonify({
        'message': f'{count} notifications marked as read',
        'count': count
    }), 200
