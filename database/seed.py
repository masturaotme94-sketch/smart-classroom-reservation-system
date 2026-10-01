"""
Smart Classroom Reservation System (SCRS) - Intelligent Demonstration Data Seeding

Intelligent Seeding Policy:
- Seeding inserts demonstration records ONLY when database tables are empty.
- Before inserting demo data, each table's row count is inspected.
- If data already exists in a table, seeding for that table is skipped to protect user records.
- Existing users, departments, buildings, classrooms, reservations, notifications, and logs remain untouched.
- Production Mode strictly forbids automatic database reset or record overwriting.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database.db import init_db, get_db, backup_db, restore_db

def get_table_count(conn, table_name):
    """Return the total number of rows in the specified database table."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0

def seed_data(force=False):
    """
    Intelligently populate database with demonstration data.
    
    Args:
        force (bool): If True, forces seeding even if tables contain existing records.
                      If False (default), skips seeding for any table that already contains data.
    """
    # Ensure database schema is created safely without dropping tables
    init_db()

    conn = get_db()
    cursor = conn.cursor()

    seeded_any = False

    # 1. Departments
    if force or get_table_count(conn, 'departments') == 0:
        departments = [
            ('College of Communication and Information Technology',),
            ('College of Engineering',),
            ('College of Nursing',),
            ('College of Industrial Technology',),
            ('Student Affairs',)
        ]
        cursor.executemany("INSERT INTO departments (department_name) VALUES (?);", departments)
        print("[INFO] Seeded table 'departments'.")
        seeded_any = True
    else:
        print("[INFO] Table 'departments' already contains data. Skipping seed.")

    # 2. Buildings
    if force or get_table_count(conn, 'buildings') == 0:
        buildings = [
            ('Engineering Complex', 'ENG', 4, 'Main engineering hub containing lecture rooms, computer labs, and conference facilities.', 'Active'),
            ('Science & Technology Hall', 'SCI', 5, 'Advanced science facility with modern lecture halls and research laboratories.', 'Active')
        ]
        cursor.executemany("INSERT INTO buildings (building_name, code, num_floors, description, status) VALUES (?, ?, ?, ?, ?);", buildings)
        print("[INFO] Seeded table 'buildings'.")
        seeded_any = True
    else:
        print("[INFO] Table 'buildings' already contains data. Skipping seed.")

    # 3. Facilities Master Data
    if force or get_table_count(conn, 'facilities') == 0:
        facilities = [
            ('Projector', 'fa-video'),
            ('Air Conditioner', 'fa-snowflake'),
            ('Smart TV', 'fa-tv'),
            ('Whiteboard', 'fa-chalkboard'),
            ('Computer', 'fa-desktop'),
            ('Internet Access', 'fa-wifi')
        ]
        cursor.executemany("INSERT INTO facilities (facility_name, icon) VALUES (?, ?);", facilities)
        print("[INFO] Seeded table 'facilities'.")
        seeded_any = True
    else:
        print("[INFO] Table 'facilities' already contains data. Skipping seed.")

    # 4. Users (1 Administrator, 5 Faculty, 3 Student Officers)
    if force or get_table_count(conn, 'users') == 0:
        users = [
            # 1 Administrator
            ('System Administrator', 'admin@university.edu', generate_password_hash('admin123'), 'Administrator', 1),
            
            # 5 Faculty Accounts
            ('Dr. Robert Smith', 'prof.smith@university.edu', generate_password_hash('faculty123'), 'Faculty', 1),
            ('Dr. Sarah Davis', 'prof.davis@university.edu', generate_password_hash('faculty123'), 'Faculty', 2),
            ('Prof. James Wilson', 'prof.wilson@university.edu', generate_password_hash('faculty123'), 'Faculty', 1),
            ('Dr. Elena Rostova', 'prof.rostova@university.edu', generate_password_hash('faculty123'), 'Faculty', 2),
            ('Prof. Michael Chang', 'prof.chang@university.edu', generate_password_hash('faculty123'), 'Faculty', 3),

            # 3 Student Organization Officer Accounts
            ('Alex Lee (Computer Science Society)', 'officer.lee@university.edu', generate_password_hash('student123'), 'Student Officer', 5),
            ('Maria Chen (Robotics & AI Club)', 'officer.chen@university.edu', generate_password_hash('student123'), 'Student Officer', 5),
            ('David Miller (Engineering Student Council)', 'officer.miller@university.edu', generate_password_hash('student123'), 'Student Officer', 5)
        ]
        cursor.executemany("INSERT INTO users (name, email, password, role, department_id) VALUES (?, ?, ?, ?, ?);", users)
        print("[INFO] Seeded table 'users'.")
        seeded_any = True
    else:
        print("[INFO] Table 'users' already contains data. Skipping seed.")

    # 5. Classrooms
    if force or get_table_count(conn, 'classrooms') == 0:
        classrooms = [
            # Engineering Complex (ENG - Building ID 1)
            ('101', 1, 1, 45, 'Lecture Room', 'Available'),
            ('102', 1, 1, 60, 'Lecture Room', 'Available'),
            ('Lab 201', 1, 2, 35, 'Laboratory', 'Available'),
            ('Lab 202', 1, 2, 30, 'Laboratory', 'Available'),
            ('Conf 301', 1, 3, 20, 'Conference Room', 'Available'),

            # Science & Technology Hall (SCI - Building ID 2)
            ('105', 2, 1, 50, 'Lecture Room', 'Available'),
            ('106', 2, 1, 75, 'Lecture Room', 'Available'),
            ('Lab 205', 2, 2, 40, 'Laboratory', 'Under Maintenance'),
            ('Lab 206', 2, 2, 35, 'Laboratory', 'Available'),
            ('Conf 401', 2, 4, 25, 'Conference Room', 'Unavailable')
        ]
        cursor.executemany("INSERT INTO classrooms (room_number, building_id, floor, capacity, room_type, status) VALUES (?, ?, ?, ?, ?, ?);", classrooms)
        print("[INFO] Seeded table 'classrooms'.")
        seeded_any = True
    else:
        print("[INFO] Table 'classrooms' already contains data. Skipping seed.")

    # 6. Classroom Facilities Mappings
    if force or get_table_count(conn, 'classroom_facilities') == 0:
        cf_mapping = [
            (1, 1), (1, 2), (1, 4), (1, 6),
            (2, 1), (2, 2), (2, 3), (2, 4), (2, 6),
            (3, 1), (3, 2), (3, 4), (3, 5), (3, 6),
            (4, 1), (4, 2), (4, 5), (4, 6),
            (5, 2), (5, 3), (5, 4), (5, 6),
            (6, 1), (6, 2), (6, 4), (6, 6),
            (7, 1), (7, 2), (7, 3), (7, 4), (7, 6),
            (8, 1), (8, 4), (8, 5),
            (9, 2), (9, 4), (9, 5), (9, 6),
            (10, 2), (10, 3), (10, 6)
        ]
        cursor.executemany("INSERT INTO classroom_facilities (classroom_id, facility_id) VALUES (?, ?);", cf_mapping)
        print("[INFO] Seeded table 'classroom_facilities'.")
        seeded_any = True
    else:
        print("[INFO] Table 'classroom_facilities' already contains data. Skipping seed.")

    # 7. Sample Reservations
    if force or get_table_count(conn, 'reservations') == 0:
        today = datetime.now()
        today_str = today.strftime('%Y-%m-%d')
        yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        two_days_ago_str = (today - timedelta(days=2)).strftime('%Y-%m-%d')
        tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        next_week_str = (today + timedelta(days=3)).strftime('%Y-%m-%d')

        reservations = [
            (2, 1, today_str, '09:00', '11:00', 'CS101 Algorithms & Data Structures Lecture', 'Approved', None),
            (3, 3, today_str, '13:00', '15:00', 'PHYS201 Advanced Chemistry Lab', 'Approved', None),
            (4, 6, today_str, '11:00', '13:00', 'MATH302 Linear Algebra Lecture', 'Approved', None),
            (7, 2, tomorrow_str, '10:00', '12:00', 'CS Society General Assembly & Hackathon Prep', 'Pending', None),
            (8, 4, tomorrow_str, '14:00', '16:00', 'Robotics Team AI Sensor Testing Workshop', 'Pending', None),
            (9, 5, tomorrow_str, '15:00', '17:00', 'Engineering Student Council Monthly Meeting', 'Pending', None),
            (5, 7, yesterday_str, '08:00', '10:00', 'BIOL101 Cell Biology Lecture', 'Completed', None),
            (6, 9, two_days_ago_str, '14:00', '16:00', 'BUS205 Marketing Seminar', 'Completed', None),
            (2, 1, next_week_str, '08:00', '10:00', 'CS101 Midterm Examination Review', 'Approved', None),
            (3, 3, next_week_str, '10:00', '12:00', 'Microprocessor Hardware Experiment', 'Approved', None),
            (7, 8, today_str, '10:00', '12:00', 'Robotics Club Practice (Room in Maintenance)', 'Rejected', 'Classroom is currently undergoing AC maintenance.'),
            (4, 10, tomorrow_str, '09:00', '11:00', 'Guest Speaker Lecture (Cancelled by Organizers)', 'Cancelled', None)
        ]
        cursor.executemany("INSERT INTO reservations (user_id, classroom_id, reservation_date, start_time, end_time, purpose, status, rejection_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", reservations)
        print("[INFO] Seeded table 'reservations'.")
        seeded_any = True
    else:
        print("[INFO] Table 'reservations' already contains data. Skipping seed.")

    # 8. Notifications
    if force or get_table_count(conn, 'notifications') == 0:
        today_str = datetime.now().strftime('%Y-%m-%d')
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        notifications = [
            (2, f'Your reservation for ENG-101 on {today_str} (09:00-11:00) has been APPROVED.', 0),
            (7, f'Your reservation request for ENG-102 on {tomorrow_str} is currently PENDING administrator review.', 0),
            (8, f'Your reservation request for SCI-Lab 205 was REJECTED. Reason: Classroom is under maintenance.', 1),
            (3, f'Your reservation for ENG-Lab 201 on {today_str} has been APPROVED.', 0)
        ]
        cursor.executemany("INSERT INTO notifications (user_id, message, is_read) VALUES (?, ?, ?);", notifications)
        print("[INFO] Seeded table 'notifications'.")
        seeded_any = True
    else:
        print("[INFO] Table 'notifications' already contains data. Skipping seed.")

    # 9. Activity Logs
    if force or get_table_count(conn, 'activity_logs') == 0:
        logs = [
            (1, 'SYSTEM_INIT', 'Database initialized and seeded with sample demonstration dataset.'),
            (2, 'CREATE_RESERVATION', 'Submitted reservation for ENG-101.'),
            (1, 'APPROVE_RESERVATION', 'Approved reservation #1 for Dr. Robert Smith.')
        ]
        cursor.executemany("INSERT INTO activity_logs (user_id, action, details) VALUES (?, ?, ?);", logs)
        print("[INFO] Seeded table 'activity_logs'.")
        seeded_any = True
    else:
        print("[INFO] Table 'activity_logs' already contains data. Skipping seed.")

    conn.commit()
    conn.close()

    if seeded_any:
        print("[INFO] Database seeding complete.")
    else:
        print("[INFO] Existing data preserved. Skipping seed process.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="SCRS Database Seeding & Maintenance Utility")
    parser.add_argument('--force', action='store_true', help="Force re-seeding even if tables contain data.")
    parser.add_argument('--backup', action='store_true', help="Create a timestamped backup of the current database.")
    parser.add_argument('--restore', action='store_true', help="Restore database from the latest backup file.")
    args = parser.parse_args()

    if args.backup:
        backup_db()
    elif args.restore:
        restore_db()
    else:
        seed_data(force=args.force)
