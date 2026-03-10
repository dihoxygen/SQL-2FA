# tests/test_open_requests.py
# Tests for routes/open_requests.py: list_open, accept_view, accept.
#
# Priority: HIGH — SECURITY CRITICAL
# The most important invariant to test here is self-approval prevention:
# an operator must NEVER be able to approve their own request. The current
# implementation enforces this at the query level (requestor_id != :op_id),
# but there is NO guard in the accept() route itself, meaning a crafted
# POST bypasses the check. Both the working case and the gap are documented.

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(rows=None, fetchone=None, scalar=None):
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar
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


def _fake_request(requestor="REQR"):
    d = {
        "request_id": "uuid-5678",
        "current_status": "Z",
        "current_requested_sql": "UPDATE foo SET x=1",
        "requestor_id": requestor,
        "assigned_approver": None,
        "request_created_on": "2024-01-01",
    }
    m = MagicMock()
    m.__getitem__ = lambda self, k: d[k]
    m.get = d.get
    return m


# ---------------------------------------------------------------------------
# GET /open-requests
# ---------------------------------------------------------------------------

class TestListOpen:
    def test_page_renders(self, logged_in_client):
        engine, _ = _make_engine(rows=[])
        with patch("routes.open_requests.sql2fa_engine", engine):
            response = logged_in_client.get("/open-requests")
        assert response.status_code == 200

    def test_requires_login(self, client):
        response = client.get("/open-requests")
        assert response.status_code == 302

    def test_excludes_own_requests(self, logged_in_client):
        """
        The query must bind :op_id = current operator_id so that the
        WHERE requestor_id != :op_id clause excludes self-owned requests.
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

        with patch("routes.open_requests.sql2fa_engine", mock_engine):
            logged_in_client.get("/open-requests")

        # The session operator_id is 'TEST' — it must be used to exclude own requests
        assert captured.get("op_id") == "TEST"

    def test_date_filters_are_applied(self, logged_in_client):
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

        with patch("routes.open_requests.sql2fa_engine", mock_engine):
            logged_in_client.get("/open-requests?date_from=2024-01-01&date_to=2024-12-31")

        assert captured.get("date_from") == "2024-01-01"
        assert captured.get("date_to") == "2024-12-31"


# ---------------------------------------------------------------------------
# GET /open-requests/<request_id>  (accept_view)
# ---------------------------------------------------------------------------

class TestAcceptView:
    def test_renders_request_detail(self, logged_in_client):
        req = _fake_request()
        engine, mock_conn = _make_engine(fetchone=req)
        mock_conn.execute.return_value.mappings.return_value.fetchone.return_value = req

        with patch("routes.open_requests.sql2fa_engine", engine):
            response = logged_in_client.get("/open-requests/uuid-5678")

        assert response.status_code == 200

    def test_requires_login(self, client):
        response = client.get("/open-requests/uuid-5678")
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# POST /open-requests/<request_id>/accept
# ---------------------------------------------------------------------------

class TestAccept:
    def test_accept_calls_assign_approver(self, logged_in_client):
        captured = {}

        def capture(query, params=None):
            if params:
                captured.update(params)
            return MagicMock()

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.open_requests.sql2fa_engine", mock_engine):
            response = logged_in_client.post(
                "/open-requests/uuid-5678/accept",
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "/approvals" in response.headers["Location"]
        assert captured.get("op_id") == "TEST"
        assert captured.get("rid") == "uuid-5678"

    def test_accept_requires_login(self, client):
        response = client.post("/open-requests/uuid-5678/accept")
        assert response.status_code == 302

    # ------------------------------------------------------------------
    # KNOWN GAP: the accept() route does not verify that the operator is
    # NOT the requestor of the request. The self-approval prevention only
    # happens in list_open()'s SQL query. A crafted POST to this endpoint
    # bypasses that check. The test below documents this gap so it is
    # visible and can be fixed when the business logic layer is extended.
    # ------------------------------------------------------------------

    def test_gap_accept_does_not_prevent_self_approval(self, logged_in_client):
        """
        KNOWN GAP — documented, not yet enforced at the route level.

        An operator whose operator_id is 'TEST' can POST to accept a request
        whose requestor_id is also 'TEST' (i.e., their own request), because
        the accept() route does not query the database to check ownership
        before calling assign_approver().

        This test will PASS today (showing the gap exists) and should FAIL
        once the fix is implemented (changing it to assert 403 or a redirect
        with an error flash).
        """
        captured = {}

        def capture(query, params=None):
            if params:
                captured.update(params)
            return MagicMock()

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.open_requests.sql2fa_engine", mock_engine):
            response = logged_in_client.post(
                "/open-requests/uuid-5678/accept",
                follow_redirects=False,
            )

        # BUG: the route succeeds (302) instead of rejecting the self-approval.
        # When the bug is fixed, this line should be changed to:
        #   assert response.status_code in (302, 403)
        #   assert "error" in ... (flash message)
        assert response.status_code == 302  # Documents that no protection exists
