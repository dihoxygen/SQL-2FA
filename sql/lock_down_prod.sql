-- Group role for all human users who may connect directly
CREATE ROLE rdbms_readonly NOLOGIN;

-- Let them connect to the DB
GRANT CONNECT ON DATABASE postgres TO rdbms_readonly;

-- Let them see objects in the schema
GRANT USAGE ON SCHEMA prod TO rdbms_readonly;

-- Allow SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA prod TO rdbms_readonly;

-- If they need to query sequences (often not needed for SELECT-only, but safe)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA prod TO rdbms_readonly;

-- Ensure future tables are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA prod
GRANT SELECT ON TABLES TO rdbms_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA prod
GRANT USAGE, SELECT ON SEQUENCES TO rdbms_readonly;


-- Remove any accidental write permissions from the group role
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA prod FROM rdbms_readonly;
REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA prod FROM rdbms_readonly;


--granting read only role to test users
CREATE ROLE garrett_login
LOGIN
PASSWORD 'gSkurkaDurk29!';

CREATE ROLE anthony_login
LOGIN
PASSWORD 'OppenVaderJabra88*';

CREATE ROLE Yen_Yao_login
LOGIN
PASSWORD 'tester_!7980*';

GRANT rdbms_readonly TO garrett_login, anthony_login, Yen_Yao_login;


-- creating a role for the app execute function to make changes
CREATE ROLE requestAppExecutor LOGIN PASSWORD 'OppenVaderJabra88*';

GRANT USAGE ON SCHEMA prod TO requestAppExecutor;


-- granting read, insert, update, delete permissions to the requestAppExecutor role for all tables in the prod schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA prod TO requestAppExecutor;    -- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA prod TO requestAppExecutor;
