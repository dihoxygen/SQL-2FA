# tests/test_auth.py
# Tests for routes/auth.py: login, register, change_password, logout.
#
# Priority: HIGH
# Authentication is the first line of defence. Failures here let anyone
# into the system (or lock legitimate operators out).

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_engine(scalar_value):
    """Return a mock sql2fa_engine whose connections return scalar_value."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = scalar_value

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value = mock_result

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn
    return mock_engine


# ---------------------------------------------------------------------------
# GET /login
# ---------------------------------------------------------------------------

class TestLoginGet:
    def test_login_page_renders(self, client):
        """GET /login should return the login form (200 OK)."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"login" in response.data.lower()


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

class TestLoginPost:
    def test_valid_credentials_redirect_to_dashboard(self, client):
        """
        When verify_operator_password returns True the user should be
        redirected to the dashboard and their operator_id stored in session.
        """
        with patch("routes.auth.sql2fa_engine", _mock_engine(True)):
            response = client.post(
                "/login",
                data={"username": "ABCD", "password": "secret"},
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_valid_login_stores_operator_id_in_session(self, client):
        """After a successful login the session must contain operator_id."""
        with patch("routes.auth.sql2fa_engine", _mock_engine(True)):
            client.post("/login", data={"username": "ABCD", "password": "secret"})

        with client.session_transaction() as sess:
            assert sess.get("operator_id") == "ABCD"

    def test_invalid_credentials_redirect_to_login(self, client):
        """
        When verify_operator_password returns False the user should be
        redirected back to /login with a flash error.
        """
        with patch("routes.auth.sql2fa_engine", _mock_engine(False)):
            response = client.post(
                "/login",
                data={"username": "ABCD", "password": "wrong"},
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_invalid_credentials_do_not_set_session(self, client):
        """A failed login must not store operator_id in the session."""
        with patch("routes.auth.sql2fa_engine", _mock_engine(False)):
            client.post("/login", data={"username": "ABCD", "password": "wrong"})

        with client.session_transaction() as sess:
            assert "operator_id" not in sess

    def test_invalid_login_flashes_error_message(self, client):
        """The 'Invalid operator ID or password' message must appear after failure."""
        with patch("routes.auth.sql2fa_engine", _mock_engine(False)):
            response = client.post(
                "/login",
                data={"username": "ABCD", "password": "wrong"},
                follow_redirects=True,
            )
        assert b"Invalid" in response.data or b"invalid" in response.data


# ---------------------------------------------------------------------------
# GET /register
# ---------------------------------------------------------------------------

class TestRegisterGet:
    def test_register_page_renders(self, client):
        response = client.get("/register")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

class TestRegisterPost:
    def test_successful_registration_redirects_to_login(self, client):
        """
        A valid registration (matching passwords, 4-char ID) should redirect
        to /login with a success flash.
        """
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.auth.sql2fa_engine", mock_engine):
            response = client.post(
                "/register",
                data={
                    "operator_id": "ABCD",
                    "password": "password123",
                    "confirm_password": "password123",
                },
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_mismatched_passwords_redirect_back_to_register(self, client):
        """
        If the two password fields differ the user should be redirected back
        to /register without touching the database.
        """
        with patch("routes.auth.sql2fa_engine") as mock_engine:
            response = client.post(
                "/register",
                data={
                    "operator_id": "ABCD",
                    "password": "password1",
                    "confirm_password": "password2",
                },
                follow_redirects=False,
            )
            mock_engine.connect.assert_not_called()

        assert response.status_code == 302
        assert "/register" in response.headers["Location"]

    def test_operator_id_too_short_is_rejected(self, client):
        """operator_id shorter than 4 characters must be rejected before the DB call."""
        with patch("routes.auth.sql2fa_engine") as mock_engine:
            response = client.post(
                "/register",
                data={
                    "operator_id": "AB",
                    "password": "password1",
                    "confirm_password": "password1",
                },
                follow_redirects=False,
            )
            mock_engine.connect.assert_not_called()

        assert response.status_code == 302
        assert "/register" in response.headers["Location"]

    def test_operator_id_too_long_is_rejected(self, client):
        """operator_id longer than 4 characters must be rejected."""
        with patch("routes.auth.sql2fa_engine") as mock_engine:
            response = client.post(
                "/register",
                data={
                    "operator_id": "ABCDE",
                    "password": "password1",
                    "confirm_password": "password1",
                },
                follow_redirects=False,
            )
            mock_engine.connect.assert_not_called()

        assert response.status_code == 302
        assert "/register" in response.headers["Location"]

    def test_operator_id_is_uppercased(self, client):
        """
        The route calls .strip().upper() on the operator_id before using it,
        so a lowercase ID should be stored as uppercase.
        """
        captured_params = {}

        def capture_execute(query, params=None):
            if params:
                captured_params.update(params)
            return MagicMock()

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = capture_execute
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.auth.sql2fa_engine", mock_engine):
            client.post(
                "/register",
                data={
                    "operator_id": "abcd",
                    "password": "password1",
                    "confirm_password": "password1",
                },
            )

        assert captured_params.get("op_id") == "ABCD"

    def test_duplicate_operator_id_flashes_error(self, client):
        """
        A database unique-constraint error should be caught and shown as a
        flash message; the user stays on /register.
        """
        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = Exception("duplicate key value")
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.auth.sql2fa_engine", mock_engine):
            response = client.post(
                "/register",
                data={
                    "operator_id": "ABCD",
                    "password": "password1",
                    "confirm_password": "password1",
                },
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "/register" in response.headers["Location"]


# ---------------------------------------------------------------------------
# GET + POST /change-password
# ---------------------------------------------------------------------------

class TestChangePassword:
    def test_unauthenticated_user_redirected(self, client):
        """Unauthenticated access to /change-password should redirect to login."""
        response = client.get("/change-password")
        assert response.status_code == 302

    def test_authenticated_user_sees_change_password_form(self, logged_in_client):
        response = logged_in_client.get("/change-password")
        assert response.status_code == 200

    def test_mismatched_new_passwords_redirects_back(self, logged_in_client):
        response = logged_in_client.post(
            "/change-password",
            data={
                "old_password": "old",
                "new_password": "new1",
                "confirm_password": "new2",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/change-password" in response.headers["Location"]

    def test_wrong_old_password_shows_error(self, logged_in_client):
        """If old password verification fails, user stays on the form."""
        with patch("routes.auth.sql2fa_engine", _mock_engine(False)):
            response = logged_in_client.post(
                "/change-password",
                data={
                    "old_password": "wrong",
                    "new_password": "newpassword",
                    "confirm_password": "newpassword",
                },
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert "/change-password" in response.headers["Location"]

    def test_correct_old_password_allows_change(self, logged_in_client):
        """
        When old password is verified, the new password is set and the user
        is redirected to the dashboard.
        """
        # First call returns True (verify), second call is create_operator_password.
        mock_result = MagicMock()
        mock_result.scalar.side_effect = [True, None]

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("routes.auth.sql2fa_engine", mock_engine):
            response = logged_in_client.post(
                "/change-password",
                data={
                    "old_password": "correct",
                    "new_password": "newpassword",
                    "confirm_password": "newpassword",
                },
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]


# ---------------------------------------------------------------------------
# GET /logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_clears_session(self, logged_in_client):
        """After logout the session must not contain operator_id."""
        logged_in_client.get("/logout")
        with logged_in_client.session_transaction() as sess:
            assert "operator_id" not in sess

    def test_logout_redirects_to_login(self, logged_in_client):
        response = logged_in_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_logout_works_even_when_not_logged_in(self, client):
        """Calling /logout without a session should not raise an exception."""
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
