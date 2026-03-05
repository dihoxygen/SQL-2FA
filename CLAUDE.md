# CLAUDE.md — SQL-2FA Codebase Guide

## Project Overview

**SQL-2FA** (SQL Two-Factor Approval) is a Flask + PostgreSQL web application that enforces a **peer-review workflow for DML execution**. Before any INSERT/UPDATE/DELETE runs against a production database, a second operator must review and approve it. The system provides a full audit trail of every request, edit, approval, denial, and execution.

---

## Repository Structure

```
SQL-2FA/
├── app.py                  # Flask app factory & blueprint registration
├── config.py               # Environment variable loading (.env)
├── db.py                   # SQLAlchemy engine initialization (two DBs)
├── helpers.py              # Shared utilities — login_required decorator
├── requirements.txt        # Python dependencies
├── readme.md               # Minimal placeholder readme
│
├── routes/                 # Flask blueprints (one per feature area)
│   ├── auth.py             # /login, /logout, /change-password
│   ├── dashboard.py        # /dashboard (home view with queues)
│   ├── requests.py         # /requests/* (requestor workflow)
│   ├── open_requests.py    # /open-requests/* (claim unassigned requests)
│   ├── approvals.py        # /approvals/* (approver workflow)
│   └── manager.py          # /manager/* (manager oversight + DML)
│
├── sql/                    # PL/pgSQL function definitions (DDL scripts)
│   ├── approver_actions.sql
│   ├── assign_approver.sql
│   ├── cancel_actions.sql
│   ├── create_new_request.SQL
│   ├── denial_actions.sql
│   ├── edit_actions.sql
│   ├── edit_denied_request.sql
│   ├── execute_failure.sql
│   ├── execute_start.sql
│   ├── execute_success.sql
│   ├── execute_manager_dml.sql
│   └── prod_create_tables.sql   # Sample production schema
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Layout template — all pages extend this
│   ├── login.html
│   ├── change_password.html
│   ├── dashboard.html
│   ├── approvals/          # Approver workflow templates
│   ├── manager/            # Manager view templates
│   ├── open_requests/      # Open requests listing
│   └── requests/           # Requestor workflow templates
│
└── static/
    └── css/
        └── style.css       # Single stylesheet for the entire app
```

---

## Architecture

### Two-Database Design

The app maintains two separate PostgreSQL connections managed in `db.py`:

| Engine | Variable | Purpose |
|--------|----------|---------|
| Audit/control DB | `sql2fa_engine` | Stores all requests, events, and execution history |
| Production DB | `prod_engine` | The real database where approved DML is executed |

Both point to the same PostgreSQL host but use **different credentials** to enforce access control. The production engine credential (`prod_db_user`) has write access; the audit engine uses a separate schema (`sql2fa`).

### Blueprint Structure

Each feature area is a separate Flask blueprint registered in `app.py`. Routes follow this pattern:

```python
# routes/requests.py
requests_bp = Blueprint('requests', __name__, url_prefix='/requests')

@requests_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    ...
```

### Database-Centric Business Logic

**Business logic lives in the PostgreSQL database, not in Python.** PL/pgSQL functions (in `sql/`) handle all state transitions, audit logging, and data integrity. Python routes call these functions via SQLAlchemy `text()` and collect results.

Example pattern used throughout the routes:

```python
with sql2fa_engine.connect() as conn:
    result = conn.execute(
        text("SELECT * FROM sql2fa.create_new_request(:op_id, :sql_text, :reason, :issues, :target_date)"),
        {"op_id": session['operator_id'], "sql_text": sql_text, ...}
    )
    conn.commit()
    row = result.fetchone()
```

---

## Key Conventions

### Authentication & Session

- Session key: `session['operator_id']` — a 4-character operator ID (e.g., `"JDOE"`)
- All protected routes use the `@login_required` decorator from `helpers.py`
- Passwords are hashed with PostgreSQL's `crypt()` / `gen_salt('bf')` (bcrypt)
- No registration endpoint — user accounts are managed directly in the database

### SQL / Database Conventions

- Table names are **UPPERCASE** and always quoted: `"REQUESTS"`, `"REQUEST_EVENTS"`
- Schema is **lowercase**: `sql2fa`, `prod`
- Operator IDs are `CHAR(4)` throughout
- All Python-to-DB parameters use **named placeholders** via SQLAlchemy `text()` — never string interpolation
- All state transitions go through PL/pgSQL functions (never raw UPDATE statements from Python)
- Database functions use `SECURITY DEFINER` to run with elevated privileges

### Status Code System

Requests move through a lifecycle tracked by single-letter status codes:

| Code | Status | Meaning |
|------|--------|---------|
| `Z` | Submitted | New — waiting for an approver to claim it |
| `R` | Review | Claimed by an approver, under review |
| `A` | Approved | Approved, ready to execute |
| `E` | Executing | Currently being executed |
| `S` | Successful | Execution completed successfully |
| `D` | Denied | Rejected by approver |
| `C` | Cancelled | Cancelled by requestor |
| `M` | Manager DML | Manager override executed |

The `STATUS_CODES` table stores boolean flags: `request_can_be_edited`, `request_can_be_canceled`, `request_can_be_executed`. Always query these flags to determine allowed actions rather than hardcoding status checks.

### Template Conventions

- All templates extend `base.html` using `{% extends "base.html" %}`
- Flash messages use categories: `error`, `success`, `info`, `warning`
- Forms use POST for mutations, GET for display-only
- Operator ID comes from `session['operator_id']` and is used for access control in templates

### CSS Conventions

- Single file: `static/css/style.css`
- CSS custom properties (variables) defined on `:root` for theming
- Class names follow a utility-style pattern (e.g., `.btn`, `.btn-primary`, `.card`, `.table-container`)
- Modal dialogs use JavaScript `show/hide` via `display: flex` toggle

---

## Environment Variables

Create a `.env` file in the project root (never commit it):

```
# SQL2FA audit/control database
db_user=<username>
db_password=<password>
db_host=<host>
db_port=5432
db_name=<database>
db_schema=sql2fa

# Production database credentials (same host, different user)
prod_db_user=<prod_username>
prod_db_password=<prod_password>

# Flask
SECRET_KEY=<long_random_secret>
```

Connection strings are assembled in `config.py` and used in `db.py`. Both engines use `sslmode=require`.

---

## Running the Application

### Development

```bash
pip install -r requirements.txt
# Create and populate .env file
python app.py
```

App runs on `http://localhost:5000` by default.

### Production

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Database Setup

There is no migration framework. Apply SQL scripts manually in this order:

1. Create the `sql2fa` schema and tables (`REQUESTS`, `REQUEST_EVENTS`, `REQUEST_EXECUTIONS`, `STATUS_CODES`)
2. Populate `STATUS_CODES` with the status code lookup data
3. Apply all PL/pgSQL function scripts in `sql/` (order doesn't matter for functions)
4. Apply `sql/prod_create_tables.sql` to set up the sample production schema

---

## Request Workflow

```
Requestor creates request
        │
        ▼ Status: Z (Submitted)
Approver claims request (open-requests)
        │
        ▼ Status: R (Review)
Approver decision:
   ├── Approve → Status: A (Approved)
   │       │
   │       ▼
   │   Requestor executes
   │       │
   │       ├── Success → Status: S
   │       └── Failure → remains A (can retry)
   │
   └── Deny → Status: D (Denied)
           │
           ▼ Requestor can edit and resubmit
           └── Edited → Status: Z (re-enters workflow)
```

Requestors can also cancel their own requests at any status where `request_can_be_canceled = true`.

---

## Adding New Features

### Adding a New Route

1. Create handler in the appropriate blueprint file under `routes/`
2. Add `@login_required` decorator
3. If the route requires a database state change, write a PL/pgSQL function in `sql/` first
4. Add the corresponding template in `templates/<feature>/`
5. Register the blueprint in `app.py` if creating a new blueprint

### Adding a New PL/pgSQL Function

1. Create a `.sql` file in `sql/`
2. Write the function with `SECURITY DEFINER` and the `sql2fa` schema prefix
3. Call from Python using `text("SELECT sql2fa.function_name(:param)")` with named parameters
4. Always `conn.commit()` after mutations

### Adding a New Template

- Extend `base.html`: `{% extends "base.html" %}`
- Wrap content in `{% block content %}...{% endblock %}`
- Use flash messages via `{% with messages = get_flashed_messages(with_categories=true) %}`

---

## Security Considerations

- **Never** interpolate user input into SQL strings — always use named parameters with `text()`
- The `@login_required` decorator must be on every route except `/login`
- Self-approval is prevented at the application level (requestor cannot be their own approver)
- Production DB credentials are separate from audit DB credentials — keep them minimal-privilege
- `SECRET_KEY` must be a long random string in production; never hardcode it
- All function calls go through `SECURITY DEFINER` functions — the app user has limited direct table access

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.1.2 | Web framework |
| SQLAlchemy | 2.0.46 | Database abstraction |
| psycopg2 | 2.9.11 | PostgreSQL adapter |
| psycopg[pool] | — | Async-compatible PG driver with pooling |
| python-dotenv | 1.2.1 | Load `.env` files |
| gunicorn | — | Production WSGI server |

---

## Common Pitfalls

- **Two engines**: `sql2fa_engine` is for all audit/workflow queries; `prod_engine` is only for executing the approved DML against production. Don't mix them up.
- **CHAR(4) operator IDs**: The `operator_id` field is exactly 4 characters and right-padded with spaces in PostgreSQL. Strip whitespace when displaying: `operator_id.strip()`.
- **UUID primary keys**: `request_id` and `execute_id` are UUIDs. PostgreSQL generates them with `gen_random_uuid()`.
- **Status flags**: Check `STATUS_CODES` table flags before showing action buttons, don't hardcode allowed statuses.
- **Session access**: Always read `session['operator_id']` for the current user — never trust a form-submitted operator ID.
