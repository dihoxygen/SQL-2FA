
from config import DATABASE_URL, DATABASE_KEY, DATABASE_SCHEMA
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        print("Connection Successful")
except Exception as e:
    print(f"Failed to connect: {e}")
    print(DATABASE_URL)