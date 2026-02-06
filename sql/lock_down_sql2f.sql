-- Group role for all human users who may connect directly
create role rdbms_readonly nologin;

-- Let them connect to the DB
grant connect on database postgres to rdbms_readonly;

-- Let them see objects in the schema
grant usage on schema prod to rdbms_readonly;

-- Allow SELECT on all existing tables
grant select on all tables in schema prod to rdbms_readonly;

-- If they need to query sequences (often not needed for SELECT-only, but safe)
grant usage, select on all sequences in schema prod to rdbms_readonly;

-- Ensure future tables are also readable
alter default privileges in schema prod
grant select on tables to rdbms_readonly;

alter default privileges in schema prod
grant usage, select on sequences to rdbms_readonly;
