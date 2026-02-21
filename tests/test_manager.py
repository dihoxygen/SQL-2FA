# tests/test_manager.py
# Tests for routes/manager.py: manager_dashboard, manager_detail, manager_dml.
#
# Priority: HIGH — SECURITY CRITICAL
# manager_dml() executes arbitrary SQL against the production database. There
# is currently NO role check: any authenticated operator can POST to this
# endpoint and run arbitrary SQL on prod. The tests document both the existing
# behaviour and the gap.

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(rows=None, fetchone=None):
    mock_result = MagicMock()
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


def _fake_request():
    d = {
        "request_id": "uuid-manager",
        "current_status": "A",
        "current_requested_sql": "UPDATE tbl SET col=1",
        "requestor_id": "REQR",
        "assigned_approver": "APRV",
        "request_created_on": "2024-01-01",
        "requested_target_date": "2024-01-02",
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: d[k]
    m.get = d.get
    return m


# ---------------------------------------------------------------------------
# GET /manager  (manager_dashboard)
# ---------------------------------------------------------------------------

class TestManagerDashboard:
    def test_page_renders(self, logged_in_client):
        engine, _ = _make_engine(rows=[])
        with patch("routes.manager.sql2fa_engine", engine):
            response = logged_in_client.get("/manager")
        assert response.status_code == 200

    def test_requires_login(self, client):
        response = client.get("/manager")
        assert response.status_code == 302

    def test_status_filter_applied(self, logged_in_client):
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

        with patch("routes.manager.sql2fa_engine", mock_engine):
            logged_in_client.get("/manager?status=A")

        assert captured.get("status") == "A"

    def test_date_filters_applied(self, logged_in_client):
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

        with patch("routes.manager.sql2fa_engine", mock_engine):
            logged_in_client.get("/manager?date_from=2024-01-01&date_to=2024-06-30")

        assert captured.get("date_from") == "2024-01-01"
        assert captured.get("date_to") == "2024-06-30"

    def test_search_id_filter_uses_like_pattern(self, logged_in_client):
        """
        search_id should be wrapped in % signs for a LIKE query.
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

        with patch("routes.manager.sql2fa_engine", mock_engine):
            logged_in_client.get("/manager?search_id=abc123")

        assert captured.get("search_id") == "%abc123%"

    def test_shows_all_requests_not_just_own(self, logged_in_client):
        """
        Unlike my_requests, the manager view must NOT filter by operator_id.
        The params dict should not contain operator_id when no filters are set.
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

        with patch("routes.manager.sql2fa_engine", mock_engine):
            logged_in_client.get("/manager")

        assert "operator_id" not in captured


# ---------------------------------------------------------------------------
# GET /manager/<request_id>  (manager_detail)
# ---------------------------------------------------------------------------

class TestManagerDetail:
    def _setup_engine(self):
        req = _fake_request()
        call_count = [0]

        def execute_side(query, params=None):
            call_count[0] += 1
            r = MagicMock()
            if call_count[0] == 1:
                r.mappings.return_value.fetchone.return_value = req
            else:
                r.mappings.return_value.all.return_value = []
            return r

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = execute_side
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        return mock_engine

    def test_detail_renders(self, logged_in_client):
        engine = self._setup_engine()
        with patch("routes.manager.sql2fa_engine", engine):
            response = logged_in_client.get("/manager/uuid-manager")
        assert response.status_code == 200

    def test_requires_login(self, client):
        response = client.get("/manager/uuid-manager")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# GET + POST /manager/<request_id>/dml
# ---------------------------------------------------------------------------

class TestManagerDml:
    def test_get_renders_form(self, logged_in_client):
        req = _fake_request()
        engine, mock_conn = _make_engine(fetchone=req)
        mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = req

        with patch("routes.manager.sql2fa_engine", engine):
            response = logged_in_client.get("/manager/uuid-manager/dml")

        assert response.status_code == 200

    def test_post_executes_sql_and_logs_it(self, logged_in_client):
        """
        A successful manager DML POST must:
        1. Execute the SQL on prod_engine.
        2. Call execute_manager_dml() on sql2fa_engine.
        3. Redirect back to the manager detail page.
        """
        sql2fa_engine_mock, sql2fa_conn = _make_engine()

        prod_conn = MagicMock()
        prod_conn.__enter__ = lambda s: prod_conn
        prod_conn.__exit__ = MagicMock(return_value=False)
        prod_conn.execute.return_value = MagicMock()
        prod_engine_mock = MagicMock()
        prod_engine_mock.connect.return_value = prod_conn

        with patch("routes.manager.sql2fa_engine", sql2fa_engine_mock), \
             patch("routes.manager.prod_engine", prod_engine_mock):
            response = logged_in_client.post(
                "/manager/uuid-manager/dml",
                data={
                    "manager_sql": "UPDATE audit_log SET reviewed=true",
                    "reason": "Emergency fix",
                },
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "uuid-manager" in response.headers["Location"]
        prod_conn.execute.assert_called_once()
        sql2fa_conn.execute.assert_called_once()

    def test_post_handles_prod_error_gracefully(self, logged_in_client):
        """
        When prod execution fails, the route must catch the exception,
        flash an error, and redirect back (not crash with 500).
        It should NOT call execute_manager_dml() since the operation failed.
        """
        sql2fa_engine_mock, sql2fa_conn = _make_engine()

        prod_conn = MagicMock()
        prod_conn.__enter__ = lambda s: prod_conn
        prod_conn.__exit__ = MagicMock(return_value=False)
        prod_conn.execute.side_effect = Exception("syntax error in SQL")
        prod_engine_mock = MagicMock()
        prod_engine_mock.connect.return_value = prod_conn

        with patch("routes.manager.sql2fa_engine", sql2fa_engine_mock), \
             patch("routes.manager.prod_engine", prod_engine_mock):
            response = logged_in_client.post(
                "/manager/uuid-manager/dml",
                data={
                    "manager_sql": "INVALID SQL !!!",
                    "reason": "Test error handling",
                },
                follow_redirects=False,
            )

        assert response.status_code == 302
        # The sql2fa logging function must NOT be called when prod fails
        sql2fa_conn.execute.assert_not_called()

    def test_requires_login(self, client):
        response = client.get("/manager/uuid-manager/dml")
        assert response.status_code == 302

    # ------------------------------------------------------------------
    # KNOWN SECURITY GAP: No role-based access control
    # ------------------------------------------------------------------

    def test_gap_any_authenticated_user_can_reach_manager_dml(self, logged_in_client):
        """
        KNOWN SECURITY GAP — documented, not yet enforced.

        The manager_dml() route only requires @login_required. Any operator
        — not just managers — can POST to this endpoint and execute arbitrary
        SQL against the production database.

        This test documents that a non-manager user (operator_id='TEST') can
        successfully reach the DML form. When role-based access control is
        added, this test should be updated to expect a 403 or redirect with
        an error flash for non-manager users.
        """
        req = _fake_request()
        engine, mock_conn = _make_engine(fetchone=req)
        mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = req

        with patch("routes.manager.sql2fa_engine", engine):
            response = logged_in_client.get("/manager/uuid-manager/dml")

        # BUG: a non-manager should not get 200 here.
        # When RBAC is added, change this to: assert response.status_code == 403
        assert response.status_code == 200  # Documents the missing RBAC check
