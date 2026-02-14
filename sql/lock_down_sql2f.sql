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
