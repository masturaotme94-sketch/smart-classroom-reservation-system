import csv
import io
from flask import Blueprint, request, jsonify, session, Response
from datetime import datetime
from database.db import query_db

report_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@report_bp.route('/summary', methods=['GET'])
def get_dashboard_summary():
    """Retrieve statistical counters for the main system dashboard."""
    today_str = datetime.now().strftime('%Y-%m-%d')

    total_rooms = query_db("SELECT COUNT(*) as cnt FROM classrooms", one=True)['cnt']
    available_rooms = query_db("SELECT COUNT(*) as cnt FROM classrooms WHERE status = 'Available'", one=True)['cnt']
    total_reservations = query_db("SELECT COUNT(*) as cnt FROM reservations", one=True)['cnt']
    pending_reservations = query_db("SELECT COUNT(*) as cnt FROM reservations WHERE status = 'Pending'", one=True)['cnt']
    approved_reservations = query_db("SELECT COUNT(*) as cnt FROM reservations WHERE status = 'Approved'", one=True)['cnt']
    today_reservations = query_db("SELECT COUNT(*) as cnt FROM reservations WHERE reservation_date = ?", (today_str,), one=True)['cnt']

    return jsonify({
        'total_classrooms': total_rooms,
        'available_classrooms': available_rooms,
        'total_reservations': total_reservations,
        'pending_reservations': pending_reservations,
        'approved_reservations': approved_reservations,
        'today_reservations': today_reservations
    })

@report_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Retrieve room utilization charts and activity metrics."""
    # 1. Most Used Classrooms
    most_used = query_db("""
        SELECT c.room_number, b.code as building_code, COUNT(r.reservation_id) as booking_count
        FROM reservations r
        JOIN classrooms c ON r.classroom_id = c.classroom_id
        JOIN buildings b ON c.building_id = b.building_id
        WHERE r.status IN ('Approved', 'Completed')
        GROUP BY r.classroom_id
        ORDER BY booking_count DESC
        LIMIT 5
    """)

    # 2. Most Active Faculty / Users
    most_active_users = query_db("""
        SELECT u.name, u.role, d.department_name, COUNT(r.reservation_id) as total_bookings
        FROM reservations r
        JOIN users u ON r.user_id = u.user_id
        LEFT JOIN departments d ON u.department_id = d.department_id
        GROUP BY r.user_id
        ORDER BY total_bookings DESC
        LIMIT 5
    """)

    # 3. Status Distribution
    status_distribution = query_db("""
        SELECT status, COUNT(*) as count 
        FROM reservations 
        GROUP BY status
    """)

    # 4. Classroom Utilization Rate (% of rooms booked today)
    today_str = datetime.now().strftime('%Y-%m-%d')
    total_avail = query_db("SELECT COUNT(*) as cnt FROM classrooms WHERE status = 'Available'", one=True)['cnt']
    booked_today = query_db("""
        SELECT COUNT(DISTINCT classroom_id) as cnt 
        FROM reservations 
        WHERE reservation_date = ? AND status IN ('Approved', 'Pending')
    """, (today_str,), one=True)['cnt']

    utilization_rate = round((booked_today / total_avail * 100), 1) if total_avail > 0 else 0

    return jsonify({
        'most_used_classrooms': most_used,
        'most_active_users': most_active_users,
        'status_distribution': status_distribution,
        'utilization_rate': utilization_rate
    })

@report_bp.route('/filtered', methods=['GET'])
def get_filtered_report():
    """
    Generate filtered report dataset based on:
    - Date range (start_date, end_date)
    - Building
    - Classroom
    - Reservation Status
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    building_id = request.args.get('building_id')
    classroom_id = request.args.get('classroom_id')
    status = request.args.get('status')

    sql = """
        SELECT r.reservation_id, r.reservation_date, r.start_time, r.end_time, r.purpose, r.status, r.created_at,
               c.room_number, c.room_type, b.building_name, b.code as building_code,
               u.name as user_name, u.email as user_email, u.role as user_role, d.department_name
        FROM reservations r
        JOIN classrooms c ON r.classroom_id = c.classroom_id
        JOIN buildings b ON c.building_id = b.building_id
        JOIN users u ON r.user_id = u.user_id
        LEFT JOIN departments d ON u.department_id = d.department_id
        WHERE 1=1
    """
    params = []

    if start_date:
        sql += " AND r.reservation_date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND r.reservation_date <= ?"
        params.append(end_date)
    if building_id:
        sql += " AND c.building_id = ?"
        params.append(building_id)
    if classroom_id:
        sql += " AND r.classroom_id = ?"
        params.append(classroom_id)
    if status:
        sql += " AND r.status = ?"
        params.append(status)

    sql += " ORDER BY r.reservation_date DESC, r.start_time ASC"
    results = query_db(sql, params)
    return jsonify(results)

@report_bp.route('/logs', methods=['GET'])
def get_activity_logs():
    """Retrieve recent system activity logs (Administrator restricted)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin access required.'}), 403

    logs = query_db("""
        SELECT l.log_id, l.action, l.details, l.created_at, u.name as user_name, u.role as user_role
        FROM activity_logs l
        LEFT JOIN users u ON l.user_id = u.user_id
        ORDER BY l.log_id DESC
        LIMIT 100
    """)
    return jsonify(logs)

@report_bp.route('/export/excel', methods=['GET'])
def export_report_excel():
    """Stream filtered reservation report as a downloadable CSV file."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    building_id = request.args.get('building_id')
    status = request.args.get('status')

    sql = """
        SELECT r.reservation_id, r.reservation_date, r.start_time, r.end_time, r.purpose, r.status,
               c.room_number, b.building_name, u.name as user_name, u.role as user_role
        FROM reservations r
        JOIN classrooms c ON r.classroom_id = c.classroom_id
        JOIN buildings b ON c.building_id = b.building_id
        JOIN users u ON r.user_id = u.user_id
        WHERE 1=1
    """
    params = []
    if start_date:
        sql += " AND r.reservation_date >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND r.reservation_date <= ?"
        params.append(end_date)
    if building_id:
        sql += " AND c.building_id = ?"
        params.append(building_id)
    if status:
        sql += " AND r.status = ?"
        params.append(status)

    sql += " ORDER BY r.reservation_date DESC"
    results = query_db(sql, params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Reservation ID', 'Date', 'Time Slot', 'Classroom', 'Building', 'User Name', 'Role', 'Purpose', 'Status'])

    for row in results:
        writer.writerow([
            f"#{row['reservation_id']}",
            row['reservation_date'],
            f"{row['start_time']} - {row['end_time']}",
            row['room_number'],
            row['building_name'],
            row['user_name'],
            row['user_role'],
            row['purpose'],
            row['status']
        ])

    output.seek(0)
    filename = f"SCRS_Reservations_Report_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
