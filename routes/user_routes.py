from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from database.db import query_db, execute_db

user_bp = Blueprint('users', __name__, url_prefix='/api/users')

def is_admin():
    return session.get('role') == 'Administrator'

@user_bp.route('', methods=['GET'])
def list_users():
    """List all system users with department names (Administrator restricted)."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    users = query_db("""
        SELECT u.user_id, u.name, u.email, u.role, u.department_id, u.created_at, d.department_name 
        FROM users u 
        LEFT JOIN departments d ON u.department_id = d.department_id 
        ORDER BY u.user_id DESC
    """)
    return jsonify(users)

@user_bp.route('/<int:user_id>', methods=['GET'])
def get_user_detail(user_id):
    """Get details for a single user (Administrator restricted)."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    user = query_db("""
        SELECT u.user_id, u.name, u.email, u.role, u.department_id, u.created_at, d.department_name
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.department_id
        WHERE u.user_id = ?
    """, (user_id,), one=True)

    if not user:
        return jsonify({'error': 'User not found.'}), 404

    return jsonify(user)

@user_bp.route('', methods=['POST'])
def create_user():
    """Create a new user account with hashed password (Administrator restricted)."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'Faculty').strip()
    department_id = data.get('department_id')

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required.'}), 400

    if role not in ['Administrator', 'Faculty', 'Student Officer']:
        return jsonify({'error': 'Invalid role specified.'}), 400

    existing = query_db("SELECT user_id FROM users WHERE email = ?", (email,), one=True)
    if existing:
        return jsonify({'error': 'Email address is already registered.'}), 400

    hashed_pw = generate_password_hash(password)
    user_id = execute_db(
        "INSERT INTO users (name, email, password, role, department_id) VALUES (?, ?, ?, ?, ?)",
        (name, email, hashed_pw, role, department_id if department_id else None)
    )

    execute_db(
        "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
        (session.get('user_id'), 'CREATE_USER', f"Created new user {name} ({role})")
    )

    return jsonify({'message': 'User created successfully.', 'user_id': user_id}), 201

@user_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update existing user information with optional password change (Administrator restricted)."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '').strip()
    department_id = data.get('department_id')
    password = data.get('password', '').strip()

    if not name or not email or not role:
        return jsonify({'error': 'Name, email, and role are required.'}), 400

    if role not in ['Administrator', 'Faculty', 'Student Officer']:
        return jsonify({'error': 'Invalid role specified.'}), 400

    existing = query_db("SELECT user_id FROM users WHERE email = ? AND user_id != ?", (email, user_id), one=True)
    if existing:
        return jsonify({'error': 'Email is already in use by another account.'}), 400

    if password:
        hashed_pw = generate_password_hash(password)
        execute_db(
            "UPDATE users SET name = ?, email = ?, password = ?, role = ?, department_id = ? WHERE user_id = ?",
            (name, email, hashed_pw, role, department_id if department_id else None, user_id)
        )
    else:
        execute_db(
            "UPDATE users SET name = ?, email = ?, role = ?, department_id = ? WHERE user_id = ?",
            (name, email, role, department_id if department_id else None, user_id)
        )

    execute_db(
        "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
        (session.get('user_id'), 'UPDATE_USER', f"Updated user ID {user_id} ({name})")
    )

    return jsonify({'message': 'User updated successfully.'})

@user_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user account (Administrator restricted)."""
    if not is_admin():
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own active administrator account.'}), 400

    target = query_db("SELECT name FROM users WHERE user_id = ?", (user_id,), one=True)
    if not target:
        return jsonify({'error': 'User not found.'}), 404

    execute_db("DELETE FROM users WHERE user_id = ?", (user_id,))
    execute_db(
        "INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
        (session.get('user_id'), 'DELETE_USER', f"Deleted user ID {user_id} ({target['name']})")
    )
    return jsonify({'message': 'User deleted successfully.'})
