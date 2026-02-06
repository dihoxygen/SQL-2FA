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



-- Remove any accidental write permissions from the group role
revoke insert, update, delete on all tables in schema prod from rdbms_readonly;
revoke truncate, references, trigger on all tables in schema prod from rdbms_readonly;


--granting read only role to test users
create role garrett_login
login
password 'gSkurkaDurk29!';

create role anthony_login
login
password 'OppenVaderJabra88*';

create role Yen_Yao_login
login
password 'tester_!7980*';

grant rdbms_readonly to garrett_login, anthony_login, Yen_Yao_login


-- creating a role for the app execute function to make changes
create role requestAppExecutor login password 'OppenVaderJabra88*';

grant usage on schema prod to requestAppExecutor;