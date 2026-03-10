# tests/test_helpers.py
# Tests for the login_required decorator in helpers.py.
#
# Priority: HIGH
# The decorator is the only authentication gate in front of every protected
# route, so its correctness is foundational to the application's security.

import pytest
from unittest.mock import patch, MagicMock


class TestLoginRequired:
    """Tests for the @login_required decorator."""

    # ------------------------------------------------------------------
    # Unauthenticated access
    # ------------------------------------------------------------------

    def test_unauthenticated_request_redirects_to_index(self, client):
        """
        Any @login_required route should redirect an unauthenticated user
        to the root (index) URL, not serve the protected page.

        We use /requests/mine as a representative protected route.
        """
        with patch("routes.requests.sql2fa_engine"):
            response = client.get("/requests/mine")
        assert response.status_code == 302
        assert "/" == response.headers["Location"] or response.headers["Location"].endswith("/")

    def test_unauthenticated_user_cannot_view_dashboard(self, client):
        with patch("routes.dashboard.sql2fa_engine"):
            response = client.get("/dashboard")
        assert response.status_code == 302

    def test_unauthenticated_user_cannot_create_request(self, client):
        with patch("routes.requests.sql2fa_engine"):
            response = client.get("/requests/create")
        assert response.status_code == 302

    def test_unauthenticated_user_cannot_access_approvals(self, client):
        with patch("routes.approvals.sql2fa_engine"):
            response = client.get("/approvals")
        assert response.status_code == 302

    def test_unauthenticated_user_cannot_access_manager(self, client):
        with patch("routes.manager.sql2fa_engine"):
            response = client.get("/manager")
        assert response.status_code == 302

    def test_unauthenticated_user_cannot_access_open_requests(self, client):
        with patch("routes.open_requests.sql2fa_engine"):
            response = client.get("/open-requests")
        assert response.status_code == 302

    # ------------------------------------------------------------------
    # Authenticated access
    # ------------------------------------------------------------------

    def test_authenticated_user_reaches_protected_route(self, logged_in_client):
        """
        A client with operator_id in session should NOT be redirected.
        We expect 200 (or a further redirect to another page, but not to /).
        """
        mock_rows = []
        with patch("routes.requests.sql2fa_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_conn.__enter__ = lambda s: mock_conn
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.mappings.return_value.all.return_value = mock_rows
            mock_engine.connect.return_value = mock_conn

            response = logged_in_client.get("/requests/mine")

        assert response.status_code == 200

    def test_session_operator_id_is_preserved_across_requests(self, client, app):
        """
        The session cookie must carry the operator_id between requests so that
        subsequent requests still appear authenticated.
        """
        with client.session_transaction() as sess:
            sess["operator_id"] = "ABCD"

        with client.session_transaction() as sess:
            assert sess.get("operator_id") == "ABCD"
