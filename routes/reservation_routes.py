from flask import Blueprint, request, jsonify, session
from datetime import datetime
from database.db import query_db, execute_db

reservation_bp = Blueprint('reservations', __name__, url_prefix='/api')

def check_time_conflict(classroom_id, res_date, start_time, end_time, exclude_reservation_id=None):
    """
    Core Smart Conflict Detection logic:
    Checks if classroom_id already has an Approved or Pending reservation overlapping [start_time, end_time] on res_date.
    """
    sql = """
        SELECT r.*, u.name as reserved_by, u.role as user_role
        FROM reservations r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.classroom_id = ? 
        AND r.reservation_date = ?
        AND r.status IN ('Pending', 'Approved')
        AND NOT (r.end_time <= ? OR r.start_time >= ?)
    """
    params = [classroom_id, res_date, start_time, end_time]
    
    if exclude_reservation_id:
        sql += " AND r.reservation_id != ?"
        params.append(exclude_reservation_id)

    return query_db(sql, params)

def find_available_alternatives(res_date, start_time, end_time, requested_capacity=0, requested_building_id=None):
    """
    Auto-suggest available alternative classrooms for the exact schedule.
    """
    sql = """
        SELECT c.*, b.building_name, b.code as building_code 
        FROM classrooms c
        JOIN buildings b ON c.building_id = b.building_id
        WHERE c.status = 'Available'
    """
    params = []

    if requested_capacity:
        sql += " AND c.capacity >= ?"
        params.append(requested_capacity)

    sql += " ORDER BY c.capacity ASC"
    all_rooms = query_db(sql, params)

    available_alternatives = []
    for room in all_rooms:
        conflicts = check_time_conflict(room['classroom_id'], res_date, start_time, end_time)
        if not conflicts:
            # Fetch facilities
            facs = query_db("""
                SELECT f.facility_name, f.icon 
                FROM facilities f
                JOIN classroom_facilities cf ON f.facility_id = cf.facility_id
                WHERE cf.classroom_id = ?
            """, (room['classroom_id'],))
            room['facilities'] = facs
            available_alternatives.append(room)
            if len(available_alternatives) >= 5: # Top 5 recommendations
                break

    return available_alternatives

@reservation_bp.route('/reservations/pending', methods=['GET'])
def get_pending_reservations():
    """Retrieve all pending reservations for the Admin approval queue."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin permission required.'}), 403

    pending = query_db("""
        SELECT r.*, c.room_number, c.capacity, c.room_type, b.building_name, b.code as building_code,
               u.name as user_name, u.email as user_email, u.role as user_role, d.department_name
        FROM reservations r
        JOIN classrooms c ON r.classroom_id = c.classroom_id
        JOIN buildings b ON c.building_id = b.building_id
        JOIN users u ON r.user_id = u.user_id
        LEFT JOIN departments d ON u.department_id = d.department_id
        WHERE r.status = 'Pending'
        ORDER BY r.reservation_date ASC, r.start_time ASC
    """)
    return jsonify(pending)

@reservation_bp.route('/reservations', methods=['GET'])
def get_reservations():
    """List reservations with RBAC scoping and multi-parameter search/filters."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized. Please login.'}), 401

    role = session.get('role')
    user_id = session.get('user_id')

    date_filter = request.args.get('date')
    building_id = request.args.get('building_id')
    classroom_id = request.args.get('classroom_id')
    status = request.args.get('status')
    search = request.args.get('search', '').strip()

    sql = """
        SELECT r.*, c.room_number, c.capacity, c.room_type, b.building_name, b.code as building_code,
               u.name as user_name, u.email as user_email, u.role as user_role, d.department_name
        FROM reservations r
        JOIN classrooms c ON r.classroom_id = c.classroom_id
        JOIN buildings b ON c.building_id = b.building_id
        JOIN users u ON r.user_id = u.user_id
        LEFT JOIN departments d ON u.department_id = d.department_id
        WHERE 1=1
    """
    params = []

    # Non-admin users see their own reservations unless viewing public schedule calendar
    if role != 'Administrator' and not request.args.get('all'):
        sql += " AND r.user_id = ?"
        params.append(user_id)

    if date_filter:
        sql += " AND r.reservation_date = ?"
        params.append(date_filter)
    if building_id:
        sql += " AND c.building_id = ?"
        params.append(building_id)
    if classroom_id:
        sql += " AND r.classroom_id = ?"
        params.append(classroom_id)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    if search:
        term = f"%{search}%"
        sql += """ AND (
            c.room_number LIKE ? OR 
            b.building_name LIKE ? OR 
            u.name LIKE ? OR 
            r.purpose LIKE ? OR
            r.reservation_date LIKE ?
        )"""
        params.extend([term, term, term, term, term])

    sql += " ORDER BY r.reservation_date DESC, r.start_time ASC"
    reservations = query_db(sql, params)
    return jsonify(reservations)

@reservation_bp.route('/reservations', methods=['POST'])
def create_reservation():
    """Submit a new reservation request with Smart Conflict Detection and validation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized. Please login.'}), 401

    data = request.get_json() or {}
    user_id = session.get('user_id')
    classroom_id = data.get('classroom_id')
    res_date = data.get('reservation_date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time = data.get('end_time', '').strip()
    purpose = data.get('purpose', '').strip()

    # 1. Validation: Blank fields
    if not classroom_id or not res_date or not start_time or not end_time or not purpose:
        return jsonify({'error': 'All fields (classroom, date, start time, end time, and purpose) are required.'}), 400

    # 2. Validation: Past date check
    today_str = datetime.now().strftime('%Y-%m-%d')
    if res_date < today_str:
        return jsonify({'error': 'Reservations cannot be made for past dates.'}), 400

    # 3. Validation: Time range validity (start_time must be < end_time)
    if start_time >= end_time:
        return jsonify({'error': 'Invalid time range. Start time must be earlier than end time.'}), 400

    # 4. Check target classroom status
    target_room = query_db("""
        SELECT c.*, b.building_name 
        FROM classrooms c 
        JOIN buildings b ON c.building_id = b.building_id 
        WHERE c.classroom_id = ?
    """, (classroom_id,), one=True)

    if not target_room:
        return jsonify({'error': 'Selected classroom does not exist.'}), 404

    if target_room['status'] != 'Available':
        return jsonify({
            'error': f"Classroom {target_room['room_number']} is currently marked as '{target_room['status']}' and cannot be reserved."
        }), 400

    # 5. Smart Conflict Detection
    conflicts = check_time_conflict(classroom_id, res_date, start_time, end_time)
    if conflicts:
        # Generate alternative classroom recommendations for the user
        alternatives = find_available_alternatives(
            res_date, start_time, end_time, 
            requested_capacity=target_room['capacity'],
            requested_building_id=target_room['building_id']
        )
        
        conflict_detail = conflicts[0]
        return jsonify({
            'conflict': True,
            'error': 'This classroom is already reserved during the selected schedule.',
            'conflict_details': {
                'reserved_by': conflict_detail['reserved_by'],
                'user_role': conflict_detail['user_role'],
                'purpose': conflict_detail['purpose'],
                'existing_start': conflict_detail['start_time'],
                'existing_end': conflict_detail['end_time'],
                'status': conflict_detail['status']
            },
            'suggested_classrooms': alternatives
        }), 409

    # 6. Save reservation
    # Initial status: Admin -> Approved, Faculty/Student -> Pending
    initial_status = 'Pending'

    res_id = execute_db("""
        INSERT INTO reservations (user_id, classroom_id, reservation_date, start_time, end_time, purpose, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, classroom_id, res_date, start_time, end_time, purpose, initial_status))

    # Send Notification to Admin & User
    msg = f"Reservation #{res_id} for Room {target_room['room_number']} on {res_date} ({start_time}-{end_time}) submitted successfully."
    execute_db("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, msg))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (user_id, 'CREATE_RESERVATION', f"Created reservation #{res_id} for Room {target_room['room_number']}"))

    return jsonify({
        'message': 'Reservation submitted successfully.',
        'reservation_id': res_id,
        'status': initial_status
    }), 201

@reservation_bp.route('/reservations/<int:reservation_id>/status', methods=['PUT'])
def update_reservation_status(reservation_id):
    """Approval Workflow: Admin approves, rejects, or completes a reservation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized.'}), 401

    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Only administrators can approve or reject reservations.'}), 403

    data = request.get_json() or {}
    new_status = data.get('status')
    rejection_reason = data.get('rejection_reason', '').strip()

    if new_status not in ['Approved', 'Rejected', 'Cancelled', 'Completed']:
        return jsonify({'error': 'Invalid status update.'}), 400

    res = query_db("""
        SELECT r.*, c.room_number, u.user_id, u.name 
        FROM reservations r
        JOIN classrooms c ON r.classroom_id = c.classroom_id
        JOIN users u ON r.user_id = u.user_id
        WHERE r.reservation_id = ?
    """, (reservation_id,), one=True)

    if not res:
        return jsonify({'error': 'Reservation record not found.'}), 404

    execute_db("""
        UPDATE reservations 
        SET status = ?, rejection_reason = ? 
        WHERE reservation_id = ?
    """, (new_status, rejection_reason if new_status == 'Rejected' else None, reservation_id))

    # Notify User
    if new_status == 'Approved':
        notif_msg = f"Good news! Your reservation for Room {res['room_number']} on {res['reservation_date']} ({res['start_time']}-{res['end_time']}) has been APPROVED."
    elif new_status == 'Rejected':
        notif_msg = f"Your reservation request for Room {res['room_number']} on {res['reservation_date']} was REJECTED. Reason: {rejection_reason or 'No reason provided.'}"
    else:
        notif_msg = f"Reservation for Room {res['room_number']} on {res['reservation_date']} was updated to {new_status}."

    execute_db("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (res['user_id'], notif_msg))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), f'{new_status.upper()}_RESERVATION', f"Set reservation #{reservation_id} to {new_status}"))

    return jsonify({'message': f'Reservation status updated to {new_status}.'})

@reservation_bp.route('/reservations/<int:reservation_id>/cancel', methods=['PUT'])
def cancel_reservation(reservation_id):
    """User or Admin cancels a reservation."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized.'}), 401

    res = query_db("SELECT * FROM reservations WHERE reservation_id = ?", (reservation_id,), one=True)
    if not res:
        return jsonify({'error': 'Reservation not found.'}), 404

    if session.get('role') != 'Administrator' and res['user_id'] != session.get('user_id'):
        return jsonify({'error': 'You can only cancel your own reservations.'}), 403

    execute_db("UPDATE reservations SET status = 'Cancelled' WHERE reservation_id = ?", (reservation_id,))
    execute_db("INSERT INTO notifications (user_id, message) VALUES (?, ?)", 
               (res['user_id'], f"Reservation #{reservation_id} has been cancelled."))

    return jsonify({'message': 'Reservation cancelled successfully.'})
