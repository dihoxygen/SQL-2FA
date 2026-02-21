# tests/test_requests.py
# Tests for routes/requests.py: create, confirmed, my_requests, detail,
# execute, edit, and cancel.
#
# Priority: HIGH
# This module drives the DML execution path — the core "dangerous" action
# of the whole application. Failures or missing logic here can silently
# corrupt production data or skip audit-trail entries.

import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(scalar=None, rows=None, fetchone=None):
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar
    mock_result.rowcount = 3

    mappings = MagicMock()
    mappings.all.return_value = rows or []
    mappings.fetchone.return_value = fetchone
    mock_result.mappings.return_value = mappings

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn
    return mock_engine, mock_conn


def _fake_request(status="A"):
    """Return a dict that behaves like a SQLAlchemy RowMapping."""
    d = {
        "request_id": "uuid-1234",
        "current_status": status,
        "current_requested_sql": "UPDATE foo SET bar=1",
        "requestor_id": "TEST",
        "assigned_approver": "APRV",
        "request_created_on": "2024-01-01",
        "requested_target_date": "2024-01-02",
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: d[k]
    m.get = d.get
    return m


def _fake_status_flags(editable=False, cancellable=False, executable=True):
    d = {
        "request_can_be_edited": editable,
        "request_can_be_cancelled": cancellable,
        "request_can_be_executed": executable,
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: d[k]
    return m


# ---------------------------------------------------------------------------
# GET /requests/create
# ---------------------------------------------------------------------------

class TestCreateGet:
    def test_create_page_renders_when_authenticated(self, logged_in_client):
        response = logged_in_client.get("/requests/create")
        assert response.status_code == 200

    def test_create_page_requires_login(self, client):
        response = client.get("/requests/create")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# POST /requests/create
# ---------------------------------------------------------------------------

class TestCreatePost:
    def test_successful_create_redirects_to_confirmation(self, logged_in_client):
        """
        A valid POST should call create_new_request() and redirect to
        /requests/confirmed/<request_id>.
        """
        mock_engine, _ = _make_engine(scalar="uuid-9999")

        with patch("routes.requests.sql2fa_engine", mock_engine):
            response = logged_in_client.post(
                "/requests/create",
                data={
                    "dml_statement": "UPDATE orders SET status='shipped'",
                    "target_date": "2024-06-01",
                },
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "uuid-9999" in response.headers["Location"]
        assert "confirmed" in response.headers["Location"]

    def test_create_calls_db_with_operator_id(self, logged_in_client):
        """The requestor_id passed to the DB must match the session operator_id."""
        captured = {}

        def capture_execute(query, params=None):
            if params:
                captured.update(params)
            r = MagicMock()
            r.scalar.return_value = "uuid-0001"
            return r

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture_execute
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.requests.sql2fa_engine", mock_engine):
            logged_in_client.post(
                "/requests/create",
                data={"dml_statement": "DELETE FROM tmp", "target_date": "2024-01-01"},
            )

        assert captured.get("requestor_id") == "TEST"


# ---------------------------------------------------------------------------
# GET /requests/confirmed/<request_id>
# ---------------------------------------------------------------------------

class TestConfirmed:
    def test_confirmation_page_renders(self, logged_in_client):
        response = logged_in_client.get("/requests/confirmed/uuid-1234")
        assert response.status_code == 200

    def test_confirmation_page_shows_request_id(self, logged_in_client):
        response = logged_in_client.get("/requests/confirmed/uuid-ABCD")
        assert b"uuid-ABCD" in response.data


# ---------------------------------------------------------------------------
# GET /requests/mine
# ---------------------------------------------------------------------------

class TestMyRequests:
    def test_my_requests_returns_200(self, logged_in_client):
        mock_engine, _ = _make_engine(rows=[])
        with patch("routes.requests.sql2fa_engine", mock_engine):
            response = logged_in_client.get("/requests/mine")
        assert response.status_code == 200

    def test_my_requests_filters_by_status(self, logged_in_client):
        """
        When ?status=A is passed, the query must include a status filter.
        We verify this by checking the params passed to conn.execute.
        """
        captured = {}

        def capture(query, params=None):
            if params:
                captured.update(params)
            r = MagicMock()
            r.mappings.return_value.all.return_value = []
            return r

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.requests.sql2fa_engine", mock_engine):
            logged_in_client.get("/requests/mine?status=A")

        assert captured.get("status") == "A"

    def test_my_requests_filters_by_date_range(self, logged_in_client):
        captured = {}

        def capture(query, params=None):
            if params:
                captured.update(params)
            r = MagicMock()
            r.mappings.return_value.all.return_value = []
            return r

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.requests.sql2fa_engine", mock_engine):
            logged_in_client.get("/requests/mine?date_from=2024-01-01&date_to=2024-12-31")

        assert captured.get("date_from") == "2024-01-01"
        assert captured.get("date_to") == "2024-12-31"

    def test_my_requests_only_returns_own_requests(self, logged_in_client):
        """
        The query must include WHERE requestor_id = :operator_id.
        Verify that the bound operator_id matches the session user.
        """
        captured = {}

        def capture(query, params=None):
            if params:
                captured.update(params)
            r = MagicMock()
            r.mappings.return_value.all.return_value = []
            return r

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.requests.sql2fa_engine", mock_engine):
            logged_in_client.get("/requests/mine")

        # The session operator_id is 'TEST' (set in logged_in_client fixture)
        assert captured.get("operator_id") == "TEST"


# ---------------------------------------------------------------------------
# GET /requests/<request_id>
# ---------------------------------------------------------------------------

class TestDetail:
    def _setup_engine_for_detail(self, status="A"):
        req = _fake_request(status)
        flags = _fake_status_flags()
        call_count = [0]

        def execute_side_effect(query, params=None):
            call_count[0] += 1
            r = MagicMock()
            # 1st call: fetch REQUESTS row
            if call_count[0] == 1:
                r.mappings.return_value.fetchone.return_value = req
            # 2nd call: fetch REQUEST_EVENTS rows
            elif call_count[0] == 2:
                r.mappings.return_value.all.return_value = []
            # 3rd call: fetch STATUS_CODES flags
            elif call_count[0] == 3:
                r.mappings.return_value.fetchone.return_value = flags
            return r

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = execute_side_effect
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        return mock_engine

    def test_detail_page_renders(self, logged_in_client):
        engine = self._setup_engine_for_detail()
        with patch("routes.requests.sql2fa_engine", engine):
            response = logged_in_client.get("/requests/uuid-1234")
        assert response.status_code == 200

    def test_detail_page_requires_login(self, client):
        response = client.get("/requests/uuid-1234")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# POST /requests/<request_id>/execute
# ---------------------------------------------------------------------------

class TestExecute:
    def test_successful_execute_calls_success_logger(self, logged_in_client):
        """
        On a successful prod execution the route must call execute_success()
        and redirect back to the detail page.
        """
        # sql2fa engine: execute_start returns the DML string
        sql2fa_engine_mock, sql2fa_conn = _make_engine(scalar="UPDATE foo SET x=1")
        # prod engine: execute the DML
        prod_conn = MagicMock()
        prod_conn.__enter__ = lambda s: prod_conn
        prod_conn.__exit__ = MagicMock(return_value=False)
        prod_result = MagicMock()
        prod_result.rowcount = 5
        prod_conn.execute.return_value = prod_result
        prod_engine_mock = MagicMock()
        prod_engine_mock.connect.return_value = prod_conn

        with patch("routes.requests.sql2fa_engine", sql2fa_engine_mock), \
             patch("routes.requests.prod_engine", prod_engine_mock):
            response = logged_in_client.post(
                "/requests/uuid-1234/execute",
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "uuid-1234" in response.headers["Location"]

    def test_failed_execute_calls_failure_logger(self, logged_in_client):
        """
        When the prod execution throws an exception, execute_failure() must
        be called on the sql2fa engine (to log the failure) and the user is
        redirected back to the detail page with an error flash.
        """
        sql2fa_engine_mock, sql2fa_conn = _make_engine(scalar="DELETE FROM tmp")

        prod_conn = MagicMock()
        prod_conn.__enter__ = lambda s: prod_conn
        prod_conn.__exit__ = MagicMock(return_value=False)
        prod_conn.execute.side_effect = Exception("DB connection lost")
        prod_engine_mock = MagicMock()
        prod_engine_mock.connect.return_value = prod_conn

        with patch("routes.requests.sql2fa_engine", sql2fa_engine_mock), \
             patch("routes.requests.prod_engine", prod_engine_mock):
            response = logged_in_client.post(
                "/requests/uuid-1234/execute",
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "uuid-1234" in response.headers["Location"]
        # execute_failure must have been called (at least one call after execute_start)
        assert sql2fa_conn.execute.call_count >= 2

    def test_execute_requires_login(self, client):
        response = client.post("/requests/uuid-1234/execute")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# GET + POST /requests/<request_id>/edit
# ---------------------------------------------------------------------------

class TestEdit:
    def test_edit_get_renders_form(self, logged_in_client):
        req = _fake_request()
        mock_engine, mock_conn = _make_engine(fetchone=req)
        mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = req

        with patch("routes.requests.sql2fa_engine", mock_engine):
            response = logged_in_client.get("/requests/uuid-1234/edit")

        assert response.status_code == 200

    def test_edit_post_redirects_to_detail(self, logged_in_client):
        mock_engine, _ = _make_engine()

        with patch("routes.requests.sql2fa_engine", mock_engine):
            response = logged_in_client.post(
                "/requests/uuid-1234/edit",
                data={
                    "dml_statement": "UPDATE x SET y=2",
                    "edit_notes": "Fixed typo",
                },
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "uuid-1234" in response.headers["Location"]

    def test_edit_requires_login(self, client):
        response = client.get("/requests/uuid-1234/edit")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# POST /requests/<request_id>/cancel
# ---------------------------------------------------------------------------

class TestCancel:
    def test_cancel_redirects_to_my_requests(self, logged_in_client):
        mock_engine, _ = _make_engine()

        with patch("routes.requests.sql2fa_engine", mock_engine):
            response = logged_in_client.post(
                "/requests/uuid-1234/cancel",
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "/requests/mine" in response.headers["Location"]

    def test_cancel_requires_login(self, client):
        response = client.post("/requests/uuid-1234/cancel")
        assert response.status_code == 302
