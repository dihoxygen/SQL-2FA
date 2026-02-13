"""
Application Configuration Settings for Environment Variables
"""

import os 
from dotenv import load_dotenv
load_dotenv()

DATABASE_USER = os.getenv('user')
DATABASE_KEY = os.getenv('supabase_key')
DATABASE_PASSWORD = os.getenv('password')
DATABASE_SCHEMA = os.getenv('schema_name')
DATABASE_HOST = os.getenv('host')
DATABASE_PORT = os.getenv('port')
DATABASE_NAME = os.getenv('dbname')



DATABASE_URL = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}?sslmode=require"