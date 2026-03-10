# tests/conftest.py
# Shared pytest fixtures for the SQL-2FA test suite.
#
# All tests mock the database engines so that no real PostgreSQL connection is
# needed. The engines (sql2fa_engine and prod_engine) are patched at the module
# level inside each route file so that the Flask test client can run without a
# live database.

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Flask app fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """
    Create a Flask application instance configured for testing.

    TESTING=True disables error propagation so the test client raises
    exceptions instead of returning 500 responses.
    """
    # Patch db.py *before* importing app so that the module-level engine
    # creation (which tries to connect immediately) doesn't blow up.
    mock_engine = MagicMock()
    with patch.dict("sys.modules", {
        "db": MagicMock(sql2fa_engine=mock_engine, prod_engine=mock_engine),
    }):
        # Also prevent config.py from breaking when .env is absent.
        with patch.dict("os.environ", {
            "db_user": "test",
            "db_password": "test",
            "db_host": "localhost",
            "db_port": "5432",
            "db_name": "testdb",
            "db_schema": "sql2fa",
            "db_key": "test",
            "prod_db_user": "test",
            "prod_db_password": "test",
            "SECRET_KEY": "test-secret-key",
        }):
            from app import app as flask_app

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        # Use a simple in-memory session so tests can inspect / set session values.
        "WTF_CSRF_ENABLED": False,
    })
    yield flask_app


@pytest.fixture
def client(app):
    """HTTP test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """
    A test client that already has a session with operator_id = 'TEST'.

    Use this for any route protected by @login_required so you do not have
    to go through the login flow in every test.
    """
    with client.session_transaction() as sess:
        sess["operator_id"] = "TEST"
    return client


# ---------------------------------------------------------------------------
# Database mock helpers
# ---------------------------------------------------------------------------

def make_mock_conn(scalar_return=None, rows=None, fetchone_return=None):
    """
    Build a mock SQLAlchemy connection suitable for use as a context manager.

    Parameters
    ----------
    scalar_return : any
        Value returned by result.scalar().
    rows : list[dict] | None
        Rows returned by .mappings().all().
    fetchone_return : dict | None
        Row returned by .mappings().fetchone().
    """
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_return
    mock_result.rowcount = 1

    mappings = MagicMock()
    mappings.all.return_value = rows or []
    mappings.fetchone.return_value = fetchone_return
    mock_result.mappings.return_value = mappings

    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_result
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    return mock_engine, mock_conn, mock_result
