"""
Smart Classroom Reservation System (SCRS) - Manual Database Restore Utility

Usage:
    python database/restore.py                # Restores the latest timestamped backup
    python database/restore.py <filename>     # Restores a specific backup file
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database.db import restore_db

if __name__ == '__main__':
    target_file = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"[INFO] Starting database restore operation{' for file: ' + target_file if target_file else ''}...")
    success = restore_db(target_file)
    if success:
        print("[SUCCESS] Database restore process finished successfully.")
    else:
        print("[ERROR] Database restore process failed.")
