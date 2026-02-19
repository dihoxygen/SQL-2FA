"""
Application Configuration Settings for Environment Variables
"""

import os 
from dotenv import load_dotenv
load_dotenv()

DATABASE_USER = os.getenv('db_user')
DATABASE_KEY = os.getenv('db_key')
DATABASE_PASSWORD = os.getenv('db_password')
DATABASE_SCHEMA = os.getenv('db_schema')
DATABASE_HOST = os.getenv('db_host')
DATABASE_PORT = os.getenv('db_port')
DATABASE_NAME = os.getenv('db_name')


DATABASE_URL = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}?sslmode=require"