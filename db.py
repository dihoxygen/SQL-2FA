from config import DATABASE_URL, PROD_DATABASE_URL
from sqlalchemy import create_engine

sql2fa_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
prod_engine = create_engine(PROD_DATABASE_URL, pool_pre_ping=True)

try:
    with sql2fa_engine.connect() as connection:
        print("sql2fa engine: Connection Successful")
    with prod_engine.connect() as connection:
        print("prod engine: Connection Successful")
except Exception as e:
    print(f"Failed to connect: {e}")