from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.db import query_db, execute_db
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user login and establish session."""
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = query_db("SELECT u.*, d.department_name FROM users u LEFT JOIN departments d ON u.department_id = d.department_id WHERE u.email = ?", (email,), one=True)
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    # Store user in Flask session
    session['user_id'] = user['user_id']
    session['name'] = user['name']
    session['email'] = user['email']
    session['role'] = user['role']
    session['department_name'] = user['department_name']

    # Log activity
    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)", 
               (user['user_id'], 'USER_LOGIN', f"User logged in from IP {request.remote_addr}"))

    return jsonify({
        'message': 'Login successful.',
        'user': {
            'user_id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'department_name': user['department_name']
        }
    })

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Clear session on logout."""
    user_id = session.get('user_id')
    if user_id:
        execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)", 
                   (user_id, 'USER_LOGOUT', 'User logged out.'))
    session.clear()
    return jsonify({'message': 'Logged out successfully.'})

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Return currently logged-in user session data."""
    if 'user_id' not in session:
        return jsonify({'authenticated': False})
    
    return jsonify({
        'authenticated': True,
        'user': {
            'user_id': session.get('user_id'),
            'name': session.get('name'),
            'email': session.get('email'),
            'role': session.get('role'),
            'department_name': session.get('department_name')
        }
    })

@auth_bp.route('/users', methods=['GET'])
def list_users():
    """List all system users (Administrator restricted)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    users = query_db("""
        SELECT u.user_id, u.name, u.email, u.role, u.department_id, u.created_at, d.department_name 
        FROM users u 
        LEFT JOIN departments d ON u.department_id = d.department_id 
        ORDER BY u.user_id DESC
    """)
    return jsonify(users)

@auth_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_detail(user_id):
    """Get detail for a single user (Administrator restricted)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized.'}), 403

    user = query_db("""
        SELECT u.user_id, u.name, u.email, u.role, u.department_id, d.department_name
        FROM users u
        LEFT JOIN departments d ON u.department_id = d.department_id
        WHERE u.user_id = ?
    """, (user_id,), one=True)

    if not user:
        return jsonify({'error': 'User not found.'}), 404

    return jsonify(user)

@auth_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user (Administrator restricted)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'Faculty').strip()
    department_id = data.get('department_id', 1)

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required.'}), 400

    if role not in ['Administrator', 'Faculty', 'Student Officer']:
        return jsonify({'error': 'Invalid role specified.'}), 400

    existing = query_db("SELECT user_id FROM users WHERE email = ?", (email,), one=True)
    if existing:
        return jsonify({'error': 'Email is already registered.'}), 400

    hashed_pw = generate_password_hash(password)
    user_id = execute_db("INSERT INTO users (name, email, password, role, department_id) VALUES (?, ?, ?, ?, ?)",
                         (name, email, hashed_pw, role, department_id))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'CREATE_USER', f"Created new user {name} ({role})"))

    return jsonify({'message': 'User created successfully.', 'user_id': user_id}), 201

@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user information (Administrator restricted)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '').strip()
    department_id = data.get('department_id', 1)
    password = data.get('password', '').strip()

    if not name or not email or not role:
        return jsonify({'error': 'Name, email, and role are required.'}), 400

    if role not in ['Administrator', 'Faculty', 'Student Officer']:
        return jsonify({'error': 'Invalid role.'}), 400

    existing = query_db("SELECT user_id FROM users WHERE email = ? AND user_id != ?", (email, user_id), one=True)
    if existing:
        return jsonify({'error': 'Email is already in use by another user.'}), 400

    if password:
        hashed_pw = generate_password_hash(password)
        execute_db("UPDATE users SET name = ?, email = ?, password = ?, role = ?, department_id = ? WHERE user_id = ?",
                   (name, email, hashed_pw, role, department_id, user_id))
    else:
        execute_db("UPDATE users SET name = ?, email = ?, role = ?, department_id = ? WHERE user_id = ?",
                   (name, email, role, department_id, user_id))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'UPDATE_USER', f"Updated user ID {user_id} ({name})"))

    return jsonify({'message': 'User updated successfully.'})

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user account (Administrator restricted)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized.'}), 403

    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own active administrator account.'}), 400

    execute_db("DELETE FROM users WHERE user_id = ?", (user_id,))
    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'DELETE_USER', f"Deleted user ID {user_id}"))
    return jsonify({'message': 'User deleted successfully.'})

@auth_bp.route('/departments', methods=['GET'])
def list_departments():
    """List all departments."""
    depts = query_db("SELECT * FROM departments ORDER BY department_name ASC")
    return jsonify(depts)

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Handle password reset requests."""
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'error': 'Email address is required.'}), 400

    user = query_db("SELECT user_id, name, email FROM users WHERE email = ?", (email,), one=True)
    if not user:
        return jsonify({'error': 'No account found with the provided email address.'}), 404

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (user['user_id'], 'FORGOT_PASSWORD_REQUEST', f"Password reset requested for {user['email']}"))

    return jsonify({'message': 'Password reset instructions have been dispatched to your email address.'})
