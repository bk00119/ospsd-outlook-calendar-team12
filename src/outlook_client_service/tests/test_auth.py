"""Unit tests for authentication routes and helpers."""

from dataclasses import dataclass
from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException, Request
from outlook_client_service.routers import auth

FIXED_NOW = 1_700_000_000
EXPIRES_IN_LONG = 3600
EXPIRES_IN_SHORT = 1800
EXPECTED_EXPIRES_AT_LONG = FIXED_NOW + EXPIRES_IN_LONG
EXPECTED_EXPIRES_AT_SHORT = FIXED_NOW + EXPIRES_IN_SHORT


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

    def test_login_returns_redirect_response_when_configured(self) -> None:
        """Return a redirect response when OAuth settings are configured."""
        settings_stub = OAuthSettingsStub(
            azure_authority="https://login.example.com",
            azure_redirect_uri="http://localhost:8000/auth/callback",
            azure_client_id="client-id-123",
        )

        with patch("outlook_client_service.routers.auth.settings", settings_stub):
            response = auth.login()

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

    def test_login_raises_when_client_id_is_missing(self) -> None:
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
            auth.login()

        assert exc_info.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "AZURE_CLIENT_ID is not configured."


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


class TestRefreshAccessToken:
    """Group tests for refreshing the access token."""

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_raises_when_refresh_token_missing(
        self,
        mock_post: object,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when refresh token is missing."""

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_updates_session_and_returns_access_token(
        self,
        mock_post: object,
        request_with_session: Request,
    ) -> None:
        """Update session state and return a new access token."""

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_clears_session_and_raises_when_refresh_fails(
        self,
        mock_post: object,
        request_with_session: Request,
    ) -> None:
        """Clear the session and raise an HTTP exception when refresh fails."""

    @patch("outlook_client_service.routers.auth._store_token_data")
    @patch("outlook_client_service.routers.auth.requests.post")
    def test_refresh_access_token_raises_when_access_token_missing_after_store(
        self,
        mock_post: object,
        mock_store_token_data: object,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when access token is missing after storage."""


class TestGetValidAccessToken:
    """Group tests for retrieving a valid access token."""

    @patch("outlook_client_service.routers.auth.refresh_access_token")
    def test_get_valid_access_token_returns_existing_token_when_not_expiring(
        self,
        mock_refresh_access_token: object,
        request_with_session: Request,
    ) -> None:
        """Return the existing token when it is not near expiry."""

    @patch("outlook_client_service.routers.auth.refresh_access_token")
    def test_get_valid_access_token_refreshes_when_token_missing(
        self,
        mock_refresh_access_token: object,
        request_with_session: Request,
    ) -> None:
        """Refresh the token when session token is missing."""

    @patch("outlook_client_service.routers.auth.refresh_access_token")
    def test_get_valid_access_token_refreshes_when_token_near_expiry(
        self,
        mock_refresh_access_token: object,
        request_with_session: Request,
    ) -> None:
        """Refresh the token when current token is near expiry."""


class TestCallback:
    """Group tests for the OAuth callback route."""

    def test_callback_raises_with_error_description(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when callback includes an error description."""

    def test_callback_raises_when_code_is_missing(
        self,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when authorization code is missing."""

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_callback_stores_token_and_returns_success_message(
        self,
        mock_post: object,
        request_with_session: Request,
    ) -> None:
        """Store token data and return a success message after callback."""

    @patch("outlook_client_service.routers.auth.requests.post")
    def test_callback_raises_when_token_exchange_fails(
        self,
        mock_post: object,
        request_with_session: Request,
    ) -> None:
        """Raise an HTTP exception when token exchange fails."""
