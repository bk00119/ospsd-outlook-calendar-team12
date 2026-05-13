"""Unit tests for authentication routes and helpers."""

from dataclasses import dataclass
from http import HTTPStatus
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException, Request
from outlook_client_service.routers import auth

FIXED_NOW = 1_700_000_000
EXPIRES_IN_LONG = 3600
EXPIRES_IN_SHORT = 1800
EXPECTED_EXPIRES_AT_LONG = FIXED_NOW + EXPIRES_IN_LONG
EXPECTED_EXPIRES_AT_SHORT = FIXED_NOW + EXPIRES_IN_SHORT
REFRESH_BUFFER_SECONDS = 60


@dataclass
class OAuthSettingsStub:
    """Provide mutable OAuth settings for route tests."""

    azure_authority: str
    azure_redirect_uri: str
    azure_client_id: str
    azure_client_secret: str = "client-secret"


@pytest.fixture
def request_with_session() -> Request:
    """Create a request object with isolated session state."""
    scope: dict[str, object] = {
        "type": "http",
        "headers": [],
        "session": {},
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def clear_slack_user_token_store() -> None:
    """Clear Slack user token bindings between tests."""
    auth._slack_user_token_store.clear()
    auth._pending_slack_auth_tokens.clear()


class TestStoreTokenData:
    """Group tests for storing token data in the session."""

    def test_store_token_data_stores_access_refresh_and_expiry(
        self,
        request_with_session: Request,
    ) -> None:
        """Store access token, refresh token, and expiry metadata."""
        token_data: dict[str, object] = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": EXPIRES_IN_LONG,
        }

        with patch(
            "outlook_client_service.routers.auth.time.time",
            return_value=FIXED_NOW,
        ):
            auth._store_token_data(request_with_session, token_data)

        assert request_with_session.session["access_token"] == "access-token"
        assert request_with_session.session["refresh_token"] == "refresh-token"
        assert request_with_session.session["expires_in"] == EXPIRES_IN_LONG
        assert request_with_session.session["expires_at"] == EXPECTED_EXPIRES_AT_LONG

    def test_store_token_data_raises_when_access_token_is_missing(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when access token is missing."""
        token_data: dict[str, object] = {
            "refresh_token": "refresh-token",
            "expires_in": EXPIRES_IN_LONG,
        }

        with pytest.raises(HTTPException) as exc_info:
            auth._store_token_data(request_with_session, token_data)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Missing access token in token response."
        assert request_with_session.session == {}

    @pytest.mark.parametrize(
        "access_token",
        [None, "", 123],
    )
    def test_store_token_data_raises_when_access_token_is_invalid(
        self,
        request_with_session: Request,
        access_token: object,
    ) -> None:
        """Raise an HTTP exception when access token is invalid."""
        token_data: dict[str, object] = {
            "access_token": access_token,
            "refresh_token": "refresh-token",
        }

        with pytest.raises(HTTPException) as exc_info:
            auth._store_token_data(request_with_session, token_data)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Missing access token in token response."
        assert request_with_session.session == {}

    def test_store_token_data_allows_missing_refresh_token(
        self,
        request_with_session: Request,
    ) -> None:
        """Store token data when refresh token is absent."""
        token_data: dict[str, object] = {
            "access_token": "access-token",
            "expires_in": EXPIRES_IN_SHORT,
        }

        with patch(
            "outlook_client_service.routers.auth.time.time",
            return_value=FIXED_NOW,
        ):
            auth._store_token_data(request_with_session, token_data)

        assert request_with_session.session["access_token"] == "access-token"
        assert "refresh_token" not in request_with_session.session
        assert request_with_session.session["expires_in"] == EXPIRES_IN_SHORT
        assert request_with_session.session["expires_at"] == EXPECTED_EXPIRES_AT_SHORT



class TestLogin:
    """Group tests for the login route."""

    def test_login_returns_redirect_response_when_configured(
        self,
        request_with_session: Request,
    ) -> None:
        """Return a redirect response when OAuth settings are configured."""
        settings_stub = OAuthSettingsStub(
            azure_authority="https://login.example.com",
            azure_redirect_uri="http://localhost:8000/auth/callback",
            azure_client_id="client-id-123",
        )

        with patch("outlook_client_service.routers.auth.settings", settings_stub):
            response = auth.login(request_with_session)

        location = response.headers["location"]
        parsed = urlparse(location)
        query = parse_qs(parsed.query)

        assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
        assert parsed.scheme == "https"
        assert parsed.netloc == "login.example.com"
        assert parsed.path == "/oauth2/v2.0/authorize"
        assert query["client_id"] == ["client-id-123"]
        assert query["response_type"] == ["code"]
        assert query["redirect_uri"] == ["http://localhost:8000/auth/callback"]
        assert query["response_mode"] == ["query"]
        assert query["scope"] == [
            "offline_access https://graph.microsoft.com/Calendars.ReadWrite",
        ]
        assert "state" in query
        assert request_with_session.session[auth.SESSION_OAUTH_STATE] == query["state"][0]

    def test_login_raises_when_client_id_is_missing(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when client ID is missing."""
        settings_stub = OAuthSettingsStub(
            azure_authority="https://login.example.com",
            azure_redirect_uri="http://localhost:8000/auth/callback",
            azure_client_id="",
        )

        with patch(
            "outlook_client_service.routers.auth.settings",
            settings_stub,
        ), pytest.raises(HTTPException) as exc_info:
            auth.login(request_with_session)

        assert exc_info.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "AZURE_CLIENT_ID is not configured."


    def test_login_stores_slack_user_id_from_auth_token(
        self,
        request_with_session: Request,
    ) -> None:
        """Store Slack user ID in session when provided."""
        settings_stub = OAuthSettingsStub(
            azure_authority="https://login.example.com",
            azure_redirect_uri="http://localhost:8000/auth/callback",
            azure_client_id="client-id-123",
        )

        slack_auth_token = auth.create_slack_auth_token("U123")
        with patch("outlook_client_service.routers.auth.settings", settings_stub):
            auth.login(request_with_session, slack_auth_token=slack_auth_token)

        assert request_with_session.session[auth.SESSION_SLACK_USER_ID] == "U123"


    def test_login_raises_when_slack_auth_token_is_invalid(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise when Slack auth token cannot be resolved."""
        settings_stub = OAuthSettingsStub(
            azure_authority="https://login.example.com",
            azure_redirect_uri="http://localhost:8000/auth/callback",
            azure_client_id="client-id-123",
        )

        with patch(
            "outlook_client_service.routers.auth.settings",
            settings_stub,
        ), pytest.raises(HTTPException) as exc_info:
            auth.login(request_with_session, slack_auth_token="invalid-token")

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Invalid or expired Slack authentication token."


class TestLogout:
    """Group tests for the logout route."""

    def test_logout_clears_session_and_returns_message(
        self,
        request_with_session: Request,
    ) -> None:
        """Clear the session and return a success message."""
        request_with_session.session["access_token"] = "access-token"
        request_with_session.session["refresh_token"] = "refresh-token"

        response = auth.logout(request_with_session)

        assert request_with_session.session == {}
        assert response == {"message": "Logged out successfully."}


    def test_logout_removes_slack_user_binding(
        self,
        request_with_session: Request,
    ) -> None:
        """Remove Slack user token binding during logout."""
        request_with_session.session[auth.SESSION_SLACK_USER_ID] = "U123"
        auth._slack_user_token_store["U123"] = {"access_token": "access-token"}

        response = auth.logout(request_with_session)

        assert auth.get_slack_user_token_data("U123") is None
        assert request_with_session.session == {}
        assert response == {"message": "Logged out successfully."}



class TestSlackUserBinding:
    """Group tests for Slack user token binding helpers."""

    def test_bind_slack_user_stores_current_token_data(
        self,
        request_with_session: Request,
    ) -> None:
        """Bind current session token data to a Slack user."""
        request_with_session.session[auth.SESSION_SLACK_USER_ID] = "U123"
        request_with_session.session["access_token"] = "access-token"
        request_with_session.session["refresh_token"] = "refresh-token"
        request_with_session.session["expires_in"] = EXPIRES_IN_LONG
        request_with_session.session["expires_at"] = EXPECTED_EXPIRES_AT_LONG

        auth.bind_slack_user_to_current_session(request_with_session)

        token_data = auth.get_slack_user_token_data("U123")
        assert token_data is not None
        assert token_data["access_token"] == "access-token"
        assert token_data["refresh_token"] == "refresh-token"
        assert token_data["expires_in"] == EXPIRES_IN_LONG
        assert token_data["expires_at"] == EXPECTED_EXPIRES_AT_LONG

    def test_bind_slack_user_skips_when_slack_user_id_is_missing(
        self,
        request_with_session: Request,
    ) -> None:
        """Skip binding when Slack user ID is not stored in session."""
        request_with_session.session["access_token"] = "access-token"

        auth.bind_slack_user_to_current_session(request_with_session)

        assert auth.get_slack_user_token_data("U123") is None

    def test_bind_slack_user_skips_when_access_token_is_missing(
        self,
        request_with_session: Request,
    ) -> None:
        """Skip binding when access token is not stored in session."""
        request_with_session.session[auth.SESSION_SLACK_USER_ID] = "U123"

        auth.bind_slack_user_to_current_session(request_with_session)

        assert auth.get_slack_user_token_data("U123") is None


class TestRefreshAccessToken:
    """Group tests for refreshing the access token."""

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_raises_when_refresh_token_missing(
        self,
        mock_post: Mock,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when refresh token is missing."""
        with pytest.raises(HTTPException) as exc_info:
            auth.refresh_access_token(request_with_session)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert "Missing refresh token" in exc_info.value.detail
        mock_post.assert_not_called()

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_updates_session_and_returns_access_token(
        self,
        mock_post: Mock,
        request_with_session: Request,
    ) -> None:
        """Update session state and return a new access token."""

        class DummyResponse:
            """Provide a minimal response stub."""

            status_code = HTTPStatus.OK

            @staticmethod
            def json() -> dict[str, object]:
                return {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": EXPIRES_IN_LONG,
                }

        request_with_session.session["refresh_token"] = "old-refresh"
        mock_post.return_value = DummyResponse()

        with patch(
            "outlook_client_service.routers.auth.time.time",
            return_value=FIXED_NOW,
        ):
            token = auth.refresh_access_token(request_with_session)

        assert token == "new-access"
        assert request_with_session.session["access_token"] == "new-access"
        assert request_with_session.session["refresh_token"] == "new-refresh"
        assert request_with_session.session["expires_in"] == EXPIRES_IN_LONG
        assert request_with_session.session["expires_at"] == EXPECTED_EXPIRES_AT_LONG

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["data"]["grant_type"] == "refresh_token"

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_clears_session_and_raises_when_refresh_fails(
        self,
        mock_post: Mock,
        request_with_session: Request,
    ) -> None:
        """Clear the session and raise an HTTP exception when refresh fails."""

        class DummyResponse:
            """Provide a failing response stub."""

            status_code = HTTPStatus.BAD_REQUEST

            @staticmethod
            def json() -> dict[str, object]:
                return {"error": "invalid_grant"}

        request_with_session.session["refresh_token"] = "old-refresh"
        request_with_session.session["access_token"] = "old-access"

        mock_post.return_value = DummyResponse()

        with pytest.raises(HTTPException) as exc_info:
            auth.refresh_access_token(request_with_session)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert "Failed to refresh token" in exc_info.value.detail
        assert request_with_session.session == {}

    @patch("outlook_client_service.routers.auth._store_token_data")
    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_raises_when_access_token_missing_after_store(
        self,
        mock_post: Mock,
        mock_store_token_data: Mock,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when access token is missing after storage."""

        class DummyResponse:
            """Provide a successful response stub."""

            status_code = HTTPStatus.OK

            @staticmethod
            def json() -> dict[str, object]:
                return {"access_token": "new-access"}

        request_with_session.session["refresh_token"] = "old-refresh"
        mock_post.return_value = DummyResponse()

        # Simulate store not writing access_token
        def noop_store(_: Request, __: dict[str, object]) -> None:
            return None

        mock_store_token_data.side_effect = noop_store

        with pytest.raises(HTTPException) as exc_info:
            auth.refresh_access_token(request_with_session)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert "Missing access token in session after refresh" in exc_info.value.detail

class TestGetValidAccessToken:
    """Group tests for retrieving a valid access token."""

    @patch("outlook_client_service.routers.auth.refresh_access_token")
    def test_get_valid_access_token_returns_existing_token_when_not_expiring(
        self,
        mock_refresh_access_token: Mock,
        request_with_session: Request,
    ) -> None:
        """Return the existing token when it is not near expiry."""
        request_with_session.session["access_token"] = "existing-access"
        request_with_session.session["expires_at"] = (
            FIXED_NOW + REFRESH_BUFFER_SECONDS + 1
        )

        with patch(
            "outlook_client_service.routers.auth.time.time",
            return_value=FIXED_NOW,
        ):
            token = auth.get_valid_access_token(
                request_with_session,
                refresh_buffer_seconds=REFRESH_BUFFER_SECONDS,
            )

        assert token == "existing-access"
        mock_refresh_access_token.assert_not_called()

    @patch("outlook_client_service.routers.auth.refresh_access_token")
    def test_get_valid_access_token_refreshes_when_token_missing(
        self,
        mock_refresh_access_token: Mock,
        request_with_session: Request,
    ) -> None:
        """Refresh the token when session token is missing."""
        mock_refresh_access_token.return_value = "refreshed-access"

        token = auth.get_valid_access_token(
            request_with_session,
            refresh_buffer_seconds=REFRESH_BUFFER_SECONDS,
        )

        assert token == "refreshed-access"
        mock_refresh_access_token.assert_called_once_with(request_with_session)

    @patch("outlook_client_service.routers.auth.refresh_access_token")
    def test_get_valid_access_token_refreshes_when_token_near_expiry(
        self,
        mock_refresh_access_token: Mock,
        request_with_session: Request,
    ) -> None:
        """Refresh the token when current token is near expiry."""
        request_with_session.session["access_token"] = "existing-access"
        request_with_session.session["expires_at"] = FIXED_NOW + REFRESH_BUFFER_SECONDS
        mock_refresh_access_token.return_value = "refreshed-access"

        with patch(
            "outlook_client_service.routers.auth.time.time",
            return_value=FIXED_NOW,
        ):
            token = auth.get_valid_access_token(
                request_with_session,
                refresh_buffer_seconds=REFRESH_BUFFER_SECONDS,
            )

        assert token == "refreshed-access"
        mock_refresh_access_token.assert_called_once_with(request_with_session)


class TestCallback:
    """Group tests for the OAuth callback route."""

    def test_callback_raises_with_error_description(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when callback includes an error description."""
        with pytest.raises(HTTPException) as exc_info:
            auth.callback(
                request_with_session,
                error="access_denied",
                error_description="User denied access.",
            )

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "User denied access."

    def test_callback_raises_when_code_is_missing(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when authorization code is missing."""
        with pytest.raises(HTTPException) as exc_info:
            auth.callback(request_with_session)

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Missing authorization code."

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_callback_stores_token_and_returns_success_message(
        self,
        mock_post: Mock,
        request_with_session: Request,
    ) -> None:
        """Store token data and return a success message after callback."""

        class DummyResponse:
            """Provide a successful token response stub."""

            status_code = HTTPStatus.OK

            @staticmethod
            def json() -> dict[str, object]:
                return {
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": EXPIRES_IN_LONG,
                }

        request_with_session.session[auth.SESSION_SLACK_USER_ID] = "U123"
        request_with_session.session[auth.SESSION_OAUTH_STATE] = "oauth-state-123"
        mock_post.return_value = DummyResponse()

        with patch(
            "outlook_client_service.routers.auth.time.time",
            return_value=FIXED_NOW,
        ):
            response = auth.callback(
                request_with_session,
                code="auth-code-123",
                state="oauth-state-123",
            )

        assert response == {"message": "Authentication successful."}
        assert request_with_session.session["access_token"] == "new-access"
        assert request_with_session.session["refresh_token"] == "new-refresh"
        assert request_with_session.session["expires_in"] == EXPIRES_IN_LONG
        assert request_with_session.session["expires_at"] == EXPECTED_EXPIRES_AT_LONG

        token_data = auth.get_slack_user_token_data("U123")
        assert token_data is not None
        assert token_data["access_token"] == "new-access"
        assert token_data["refresh_token"] == "new-refresh"

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["data"]["grant_type"] == "authorization_code"
        assert call_kwargs["data"]["code"] == "auth-code-123"

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_callback_raises_when_token_exchange_fails(
        self,
        mock_post: Mock,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when token exchange fails."""

        class DummyResponse:
            """Provide a failing token response stub."""

            status_code = HTTPStatus.BAD_REQUEST

            @staticmethod
            def json() -> dict[str, object]:
                return {"error": "invalid_grant"}

        request_with_session.session[auth.SESSION_OAUTH_STATE] = "oauth-state-123"
        mock_post.return_value = DummyResponse()

        with pytest.raises(HTTPException) as exc_info:
            auth.callback(
                request_with_session,
                code="bad-code",
                state="oauth-state-123",
            )

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert "invalid_grant" in str(exc_info.value.detail)
    def test_callback_raises_when_state_is_invalid(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when OAuth state is invalid."""
        request_with_session.session[auth.SESSION_OAUTH_STATE] = "expected-state"

        with pytest.raises(HTTPException) as exc_info:
            auth.callback(
                request_with_session,
                code="auth-code-123",
                state="wrong-state",
            )

        assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST
        assert exc_info.value.detail == "Invalid OAuth state"
