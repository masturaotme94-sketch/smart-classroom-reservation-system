from flask import Blueprint, request, jsonify, session
from database.db import query_db, execute_db

classroom_bp = Blueprint('classrooms', __name__, url_prefix='/api')

@classroom_bp.route('/classrooms', methods=['GET'])
def get_classrooms():
    """List classrooms with optional filtering by building, capacity, status, room type, and facilities."""
    building_id = request.args.get('building_id')
    status = request.args.get('status')
    room_type = request.args.get('room_type')
    min_capacity = request.args.get('min_capacity')
    search = request.args.get('search', '').strip()

    sql = """
        SELECT c.*, b.building_name, b.code as building_code 
        FROM classrooms c
        JOIN buildings b ON c.building_id = b.building_id
        WHERE 1=1
    """
    params = []

    if building_id:
        sql += " AND c.building_id = ?"
        params.append(building_id)
    if status:
        sql += " AND c.status = ?"
        params.append(status)
    if room_type:
        sql += " AND c.room_type = ?"
        params.append(room_type)
    if min_capacity:
        sql += " AND c.capacity >= ?"
        params.append(min_capacity)
    if search:
        sql += " AND (c.room_number LIKE ? OR b.building_name LIKE ? OR b.code LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY b.building_name ASC, c.room_number ASC"
    classrooms = query_db(sql, params)

    # Attach facilities to each classroom
    for room in classrooms:
        facs = query_db("""
            SELECT f.facility_id, f.facility_name, f.icon 
            FROM facilities f
            JOIN classroom_facilities cf ON f.facility_id = cf.facility_id
            WHERE cf.classroom_id = ?
        """, (room['classroom_id'],))
        room['facilities'] = facs

    return jsonify(classrooms)

@classroom_bp.route('/classrooms/<int:classroom_id>', methods=['GET'])
def get_classroom_detail(classroom_id):
    """Fetch detail for a single classroom including facilities and upcoming schedule."""
    room = query_db("""
        SELECT c.*, b.building_name, b.code as building_code 
        FROM classrooms c
        JOIN buildings b ON c.building_id = b.building_id
        WHERE c.classroom_id = ?
    """, (classroom_id,), one=True)

    if not room:
        return jsonify({'error': 'Classroom not found.'}), 404

    facs = query_db("""
        SELECT f.facility_id, f.facility_name, f.icon 
        FROM facilities f
        JOIN classroom_facilities cf ON f.facility_id = cf.facility_id
        WHERE cf.classroom_id = ?
    """, (classroom_id,))
    room['facilities'] = facs

    return jsonify(room)

@classroom_bp.route('/classrooms', methods=['POST'])
def add_classroom():
    """Add a new classroom (Admin only)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin permission required.'}), 403

    data = request.get_json() or {}
    room_number = data.get('room_number', '').strip()
    building_id = data.get('building_id')
    floor = data.get('floor')
    capacity = data.get('capacity')
    room_type = data.get('room_type') # Lecture Room, Laboratory, Conference Room
    status = data.get('status', 'Available') # Available, Under Maintenance, Unavailable
    facility_ids = data.get('facility_ids', [])

    if not room_number or not building_id or not floor or not capacity or not room_type:
        return jsonify({'error': 'Room number, building, floor, capacity, and room type are required.'}), 400

    if room_type not in ['Lecture Room', 'Laboratory', 'Conference Room']:
        return jsonify({'error': 'Invalid room type.'}), 400

    existing = query_db("SELECT classroom_id FROM classrooms WHERE room_number = ? AND building_id = ?",
                        (room_number, building_id), one=True)
    if existing:
        return jsonify({'error': f'Classroom {room_number} already exists in this building.'}), 400

    cid = execute_db("""
        INSERT INTO classrooms (room_number, building_id, floor, capacity, room_type, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (room_number, building_id, floor, capacity, room_type, status))

    # Map facilities
    for fid in facility_ids:
        execute_db("INSERT INTO classroom_facilities (classroom_id, facility_id) VALUES (?, ?)", (cid, fid))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'ADD_CLASSROOM', f"Added classroom {room_number}"))

    return jsonify({'message': 'Classroom added successfully.', 'classroom_id': cid}), 201

@classroom_bp.route('/classrooms/<int:classroom_id>', methods=['PUT'])
def update_classroom(classroom_id):
    """Edit existing classroom details and facilities (Admin only)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin permission required.'}), 403

    data = request.get_json() or {}
    room_number = data.get('room_number', '').strip()
    building_id = data.get('building_id')
    floor = data.get('floor')
    capacity = data.get('capacity')
    room_type = data.get('room_type')
    status = data.get('status')
    facility_ids = data.get('facility_ids', None)

    execute_db("""
        UPDATE classrooms 
        SET room_number = ?, building_id = ?, floor = ?, capacity = ?, room_type = ?, status = ?
        WHERE classroom_id = ?
    """, (room_number, building_id, floor, capacity, room_type, status, classroom_id))

    if facility_ids is not None:
        execute_db("DELETE FROM classroom_facilities WHERE classroom_id = ?", (classroom_id,))
        for fid in facility_ids:
            execute_db("INSERT INTO classroom_facilities (classroom_id, facility_id) VALUES (?, ?)", (classroom_id, fid))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'EDIT_CLASSROOM', f"Updated classroom ID {classroom_id}"))

    return jsonify({'message': 'Classroom updated successfully.'})

@classroom_bp.route('/classrooms/<int:classroom_id>', methods=['DELETE'])
def delete_classroom(classroom_id):
    """Delete classroom (Admin only)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized.'}), 403

    execute_db("DELETE FROM classrooms WHERE classroom_id = ?", (classroom_id,))
    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'DELETE_CLASSROOM', f"Deleted classroom ID {classroom_id}"))
    return jsonify({'message': 'Classroom deleted successfully.'})

@classroom_bp.route('/buildings', methods=['GET'])
def get_buildings():
    """List buildings with total classroom counts and optional search/status filtering."""
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()

    sql = """
        SELECT b.*, 
               (SELECT COUNT(*) FROM classrooms c WHERE c.building_id = b.building_id) AS total_classrooms
        FROM buildings b
        WHERE 1=1
    """
    params = []

    if status:
        sql += " AND b.status = ?"
        params.append(status)
    if search:
        sql += " AND (b.building_name LIKE ? OR b.code LIKE ? OR b.description LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY b.building_name ASC"
    buildings = query_db(sql, params)
    return jsonify(buildings)

@classroom_bp.route('/buildings/<int:building_id>', methods=['GET'])
def get_building_detail(building_id):
    """Fetch detail for a single building including total assigned classrooms."""
    building = query_db("""
        SELECT b.*, 
               (SELECT COUNT(*) FROM classrooms c WHERE c.building_id = b.building_id) AS total_classrooms
        FROM buildings b
        WHERE b.building_id = ?
    """, (building_id,), one=True)

    if not building:
        return jsonify({'error': 'Building not found.'}), 404

    return jsonify(building)

@classroom_bp.route('/buildings', methods=['POST'])
def add_building():
    """Add a new building (Admin only)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin permission required.'}), 403

    data = request.get_json() or {}
    building_name = data.get('building_name', '').strip()
    code = data.get('code', '').strip().upper()
    num_floors = data.get('num_floors')
    description = data.get('description', '').strip()
    status = data.get('status', 'Active')

    if not building_name:
        return jsonify({'error': 'Building Name is required.'}), 400
    try:
        num_floors = int(num_floors)
        if num_floors < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'error': 'Number of floors must be a valid positive integer.'}), 400

    if not code:
        code = ''.join([w[0] for w in building_name.split() if w]).upper()[:5]

    if status not in ['Active', 'Inactive']:
        return jsonify({'error': 'Invalid status. Must be Active or Inactive.'}), 400

    existing = query_db("SELECT building_id FROM buildings WHERE building_name = ?", (building_name,), one=True)
    if existing:
        return jsonify({'error': f'Building "{building_name}" already exists.'}), 400

    bid = execute_db("""
        INSERT INTO buildings (building_name, code, num_floors, description, status)
        VALUES (?, ?, ?, ?, ?)
    """, (building_name, code, num_floors, description, status))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'ADD_BUILDING', f"Added building {building_name} (ID: {bid})"))

    return jsonify({'message': 'Building added successfully.', 'building_id': bid}), 201

@classroom_bp.route('/buildings/<int:building_id>', methods=['PUT'])
def update_building(building_id):
    """Edit existing building details (Admin only)."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized. Admin permission required.'}), 403

    data = request.get_json() or {}
    building_name = data.get('building_name', '').strip()
    code = data.get('code', '').strip().upper()
    num_floors = data.get('num_floors')
    description = data.get('description', '').strip()
    status = data.get('status', 'Active')

    if not building_name:
        return jsonify({'error': 'Building Name is required.'}), 400
    try:
        num_floors = int(num_floors)
        if num_floors < 1:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'error': 'Number of floors must be a valid positive integer.'}), 400

    if status not in ['Active', 'Inactive']:
        return jsonify({'error': 'Invalid status.'}), 400

    existing_name = query_db("SELECT building_id FROM buildings WHERE building_name = ? AND building_id != ?",
                            (building_name, building_id), one=True)
    if existing_name:
        return jsonify({'error': f'Another building with the name "{building_name}" already exists.'}), 400

    execute_db("""
        UPDATE buildings 
        SET building_name = ?, code = ?, num_floors = ?, description = ?, status = ?
        WHERE building_id = ?
    """, (building_name, code, num_floors, description, status, building_id))

    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'EDIT_BUILDING', f"Updated building ID {building_id}"))

    return jsonify({'message': 'Building updated successfully.'})

@classroom_bp.route('/buildings/<int:building_id>', methods=['DELETE'])
def delete_building(building_id):
    """Delete building (Admin only). Prevents deletion if classrooms are assigned."""
    if session.get('role') != 'Administrator':
        return jsonify({'error': 'Unauthorized.'}), 403

    bld = query_db("SELECT building_name FROM buildings WHERE building_id = ?", (building_id,), one=True)
    if not bld:
        return jsonify({'error': 'Building not found.'}), 404

    classroom_count = query_db("SELECT COUNT(*) as count FROM classrooms WHERE building_id = ?", (building_id,), one=True)['count']
    if classroom_count > 0:
        return jsonify({'error': 'This building cannot be deleted because it still contains classrooms.'}), 400

    execute_db("DELETE FROM buildings WHERE building_id = ?", (building_id,))
    execute_db("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?)",
               (session.get('user_id'), 'DELETE_BUILDING', f"Deleted building {bld['building_name']} (ID: {building_id})"))

    return jsonify({'message': 'Building deleted successfully.'})

@classroom_bp.route('/facilities', methods=['GET'])
def get_facilities():
    """List all available facilities."""
    facs = query_db("SELECT * FROM facilities ORDER BY facility_name ASC")
    return jsonify(facs)
