import os

class Config:
    """
    Smart Classroom Reservation System (SCRS) Configuration Settings
    """
    SECRET_KEY = os.environ.get('SECRET_KEY', 'scrs_secure_university_key_2026_x89f')
    DB_NAME = 'scrs.db'
    DEBUG = False
