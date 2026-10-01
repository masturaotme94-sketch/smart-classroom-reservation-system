"""
Smart Classroom Reservation System (SCRS) - Manual Database Backup Utility

Usage:
    python database/backup.py
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database.db import backup_db

if __name__ == '__main__':
    print("[INFO] Starting manual database backup...")
    path = backup_db()
    if path:
        print(f"[SUCCESS] Database backup completed: {os.path.basename(path)}")
    else:
        print("[ERROR] Database backup failed.")
