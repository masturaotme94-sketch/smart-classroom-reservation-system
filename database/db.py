"""
Smart Classroom Reservation System (SCRS) - Database Interface & Lifecycle Management

This module provides:
1. Database Connection Management with Dict-like Row Access (get_db).
2. Safe, Non-Destructive Database Schema Initialization (init_db).
3. Query Execution Helpers (query_db, execute_db).
4. Transactionally Consistent Database Backup Utility (backup_db).
5. Automatic & Manual Database Restore Utility (restore_db).
6. Helper routines for detecting database state and table row counts.

Database Persistence Policy:
- Existing tables and records are NEVER deleted or overwritten on normal application startup.
- All table creations use CREATE TABLE IF NOT EXISTS.
"""

import sqlite3
import os
import shutil
from datetime import datetime

# Absolute path to primary SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scrs.db')

# Absolute path to database backups directory
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')

def get_db(db_path=None):
    """
    Establish and return a SQLite database connection with dict-like row access.
    
    Args:
        db_path (str, optional): Target SQLite database file path. Defaults to DB_PATH.

    Returns:
        sqlite3.Connection: Database connection with row_factory set to sqlite3.Row.
    """
    target = db_path or DB_PATH
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """
    Safely initialize the database schema from schema.sql using CREATE TABLE IF NOT EXISTS.
    
    This function is strictly non-destructive. If tables already exist, their schema
    and existing data will remain intact and un-modified.
    """
    schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found at {schema_file}")
        
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    conn = get_db()
    cursor = conn.cursor()
    # Execute non-destructive schema script
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()

def is_db_initialized():
    """
    Check whether the primary database file exists and contains tables.
    
    Returns:
        bool: True if database file exists and key tables are present, False otherwise.
    """
    if not os.path.exists(DB_PATH):
        return False
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception:
        return False

def query_db(query, args=(), one=False):
    """
    Execute a read (SELECT) query and return dictionary result(s).
    
    Args:
        query (str): SQL query string.
        args (tuple): Query parameters.
        one (bool): If True, returns a single dictionary or None.
        
    Returns:
        dict or list[dict]: Result row(s) as dictionary objects.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """
    Execute a write (INSERT/UPDATE/DELETE) query and return the last row ID.
    
    Args:
        query (str): SQL statement.
        args (tuple): Query parameters.
        
    Returns:
        int: The last inserted row ID.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, args)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def backup_db(target_dir=None):
    """
    Create a timestamped backup of the database using SQLite's native backup API.
    
    Uses conn.backup() for a transactionally consistent, thread-safe snapshot 
    that safely executes even while the web server is running.
    
    Args:
        target_dir (str, optional): Directory to store backups. Defaults to database/backups.
        
    Returns:
        str: Absolute path to the newly created backup file.
    """
    if not os.path.exists(DB_PATH):
        print("[WARN] Cannot create backup: Database file does not exist.")
        return None

    dest_dir = target_dir or BACKUP_DIR
    os.makedirs(dest_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"scrs_backup_{timestamp}.db"
    backup_path = os.path.join(dest_dir, backup_filename)

    # Perform online transactionally consistent backup
    source_conn = get_db(DB_PATH)
    backup_conn = sqlite3.connect(backup_path)

    with backup_conn:
        source_conn.backup(backup_conn)

    backup_conn.close()
    source_conn.close()

    print(f"[INFO] Database backup created successfully: {backup_filename}")
    return backup_path

def restore_db(backup_file=None):
    """
    Restore the database from a backup file inside database/backups directory.
    
    If backup_file is not specified, automatically restores the latest available backup.
    Creates an emergency safety backup of the current state before replacing.
    
    Args:
        backup_file (str, optional): Filename or absolute path of backup to restore.
        
    Returns:
        bool: True if restore succeeded, False otherwise.
    """
    dest_dir = BACKUP_DIR
    if not os.path.exists(dest_dir) or not os.listdir(dest_dir):
        print("[ERROR] Restore failed: No backups found in database/backups/.")
        return False

    if backup_file is None:
        # Pick latest timestamped backup
        backups = [f for f in os.listdir(dest_dir) if f.endswith('.db')]
        if not backups:
            print("[ERROR] Restore failed: No .db backup files located.")
            return False
        backups.sort(reverse=True)
        backup_path = os.path.join(dest_dir, backups[0])
    elif os.path.isabs(backup_file):
        backup_path = backup_file
    else:
        backup_path = os.path.join(dest_dir, backup_file)

    if not os.path.exists(backup_path):
        print(f"[ERROR] Restore failed: Backup file not found at {backup_path}")
        return False

    # Take safety snapshot of existing database before restoring
    if os.path.exists(DB_PATH):
        pre_restore_backup = os.path.join(dest_dir, f"pre_restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, pre_restore_backup)
        print(f"[INFO] Pre-restore safety backup created: {os.path.basename(pre_restore_backup)}")

    # Copy backup file onto primary database location
    shutil.copy2(backup_path, DB_PATH)
    print(f"[INFO] Database restored successfully from: {os.path.basename(backup_path)}")
    return True
