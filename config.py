# config.py - Application configuration settings

import os

class Config:
    SECRET_KEY = 'jobsphere_secret_key_2024'

    # MySQL Database Configuration
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'Suraj@15'         # Change to your MySQL password
    MYSQL_DB = 'jobsphere_db'
    MYSQL_CURSORCLASS = 'DictCursor'

    # File Upload Settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads', 'pdfs')
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
