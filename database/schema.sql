-- Smart Classroom Reservation System (SCRS) Non-Destructive Database Schema
-- Uses CREATE TABLE IF NOT EXISTS to guarantee safe initialization without deleting existing data.

-- Departments Table
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_name TEXT NOT NULL UNIQUE
);

-- Buildings Table
CREATE TABLE IF NOT EXISTS buildings (
    building_id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_name TEXT NOT NULL UNIQUE,
    code TEXT UNIQUE,
    num_floors INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active', 'Inactive'))
);

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Administrator', 'Faculty', 'Student Officer')),
    department_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- Classrooms Table
CREATE TABLE IF NOT EXISTS classrooms (
    classroom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL,
    building_id INTEGER NOT NULL,
    floor INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    room_type TEXT NOT NULL CHECK (room_type IN ('Lecture Room', 'Laboratory', 'Conference Room')),
    status TEXT NOT NULL DEFAULT 'Available' CHECK (status IN ('Available', 'Under Maintenance', 'Unavailable')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (building_id) REFERENCES buildings(building_id),
    UNIQUE(room_number, building_id)
);

-- Facilities Master Table
CREATE TABLE IF NOT EXISTS facilities (
    facility_id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_name TEXT NOT NULL UNIQUE,
    icon TEXT
);

-- Classroom Facilities Mapping Table
CREATE TABLE IF NOT EXISTS classroom_facilities (
    classroom_id INTEGER NOT NULL,
    facility_id INTEGER NOT NULL,
    PRIMARY KEY (classroom_id, facility_id),
    FOREIGN KEY (classroom_id) REFERENCES classrooms(classroom_id) ON DELETE CASCADE,
    FOREIGN KEY (facility_id) REFERENCES facilities(facility_id) ON DELETE CASCADE
);

-- Reservations Table
CREATE TABLE IF NOT EXISTS reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    classroom_id INTEGER NOT NULL,
    reservation_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Cancelled', 'Completed')),
    rejection_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(classroom_id) ON DELETE CASCADE
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Activity Logs Table
CREATE TABLE IF NOT EXISTS activity_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);
