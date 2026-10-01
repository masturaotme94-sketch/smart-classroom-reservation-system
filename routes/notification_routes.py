from flask import Blueprint, jsonify, session
from database.db import query_db, execute_db

notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notification_bp.route('', methods=['GET'])
def get_user_notifications():
    """Retrieve notifications for the logged-in user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized.'}), 401

    user_id = session.get('user_id')
    notifications = query_db("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 20
    """, (user_id,))
    
    unread_count = query_db("SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,), one=True)['cnt']
    return jsonify({'notifications': notifications, 'unread_count': unread_count})

@notification_bp.route('/read-all', methods=['PUT'])
def mark_all_read():
    """Mark all notifications as read for current user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized.'}), 401

    user_id = session.get('user_id')
    execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    return jsonify({'message': 'All notifications marked as read.'})

@notification_bp.route('/<int:notification_id>/read', methods=['PUT'])
def mark_single_read(notification_id):
    """Mark a specific notification as read for current user."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized.'}), 401

    user_id = session.get('user_id')
    execute_db("UPDATE notifications SET is_read = 1 WHERE notification_id = ? AND user_id = ?", (notification_id, user_id))
    return jsonify({'message': f'Notification #{notification_id} marked as read.'})

