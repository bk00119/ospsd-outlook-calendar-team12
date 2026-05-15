"""Unit tests for service dependency providers."""

from dataclasses import dataclass
from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from outlook_client_impl.outlook_impl import OutlookClient
from outlook_client_service.routers.auth import SCOPES

from outlook_client_service import dependencies


@dataclass
class SettingsStub:
    """Mutable settings stub for dependency tests."""

    calendar_provider: str = "outlook"
    google_credentials_file: str = "credentials.json"
    google_token_file: str = "token.json"
    google_calendar_id: str = "primary"
    google_interactive_auth: bool = False


class TestCalendarProvider:
    """Test calendar provider selection helpers."""

    def test_get_calendar_provider_returns_configured_provider(self) -> None:
        """Return the provider configured in service settings."""
        with patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="google")):
            assert dependencies.get_calendar_provider() == "google"

    def test_get_google_calendar_client_builds_client_from_settings(self) -> None:
        """Build a Google client using configured Google settings."""
        mock_client = Mock()

        settings_stub = SettingsStub(
            google_credentials_file="credentials.json",
            google_token_file="token.json",
            google_calendar_id="primary",
            google_interactive_auth=False,
        )

        with (
            patch("outlook_client_service.dependencies.settings", settings_stub),
            patch(
                "outlook_client_service.dependencies.GoogleCalendarClient",
                return_value=mock_client,
            ) as google_client_factory,
        ):
            result = dependencies.get_google_calendar_client()

        assert result is mock_client
        google_client_factory.assert_called_once_with(
            credentials_file="credentials.json",
            token_file="token.json",
            calendar_id="primary",
            interactive=False,
        )


class TestCalendarClientFromAccessToken:
    """Test explicit access-token client construction."""

    def test_google_provider_returns_google_client(self) -> None:
        """Return Google client without using the Outlook access token."""
        mock_client = Mock()

        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="google")),
            patch(
                "outlook_client_service.dependencies.get_google_calendar_client",
                return_value=mock_client,
            ),
        ):
            result = dependencies.get_calendar_client_from_access_token("token")

        assert result is mock_client

    def test_invalid_provider_raises_value_error(self) -> None:
        """Reject unsupported calendar providers."""
        with (
            patch(
                "outlook_client_service.dependencies.settings",
                SettingsStub(calendar_provider="unknown"),
            ),
            pytest.raises(ValueError, match="Unsupported calendar provider"),
        ):
            dependencies.get_calendar_client_from_access_token("token")

    def test_outlook_provider_builds_client_from_graph_service(self) -> None:
        """Build Outlook client with a Graph service for the Outlook provider."""
        mock_graph_service = Mock()
        mock_calendar_client = Mock()
        client_factory = Mock(return_value=mock_calendar_client)

        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="outlook")),
            patch(
                "outlook_client_service.dependencies.get_graph_service_from_access_token",
                return_value=mock_graph_service,
            ) as graph_service_factory,
        ):
            result = dependencies.get_calendar_client_from_access_token(
                "token",
                client_factory=client_factory,
            )

        assert result is mock_calendar_client
        graph_service_factory.assert_called_once_with("token")
        client_factory.assert_called_once_with(service=mock_graph_service)


class TestSlackCalendarClient:
    """Test Slack-user calendar client construction."""

    def test_google_provider_returns_google_client_for_slack_user(self) -> None:
        """Return Google client directly in Google provider mode."""
        mock_client = Mock()

        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="google")),
            patch(
                "outlook_client_service.dependencies.get_google_calendar_client",
                return_value=mock_client,
            ),
        ):
            result = dependencies.get_calendar_client_for_slack_user("U123")

        assert result is mock_client

    def test_invalid_provider_raises_value_error_for_slack_user(self) -> None:
        """Reject unsupported providers for Slack requests."""
        with (
            patch(
                "outlook_client_service.dependencies.settings",
                SettingsStub(calendar_provider="unknown"),
            ),
            pytest.raises(ValueError, match="Unsupported calendar provider"),
        ):
            dependencies.get_calendar_client_for_slack_user("U123")

    def test_outlook_provider_returns_none_when_slack_user_is_not_linked(self) -> None:
        """Return None when an Outlook Slack user has no linked token."""
        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="outlook")),
            patch(
                "outlook_client_service.dependencies.get_valid_access_token_for_slack_user",
                return_value=None,
            ),
        ):
            result = dependencies.get_calendar_client_for_slack_user("U123")

        assert result is None

    def test_outlook_provider_uses_linked_slack_access_token(self) -> None:
        """Build a calendar client from the linked Slack user's token."""
        mock_client = Mock()

        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="outlook")),
            patch(
                "outlook_client_service.dependencies.get_valid_access_token_for_slack_user",
                return_value="linked-token",
            ),
            patch(
                "outlook_client_service.dependencies.get_calendar_client_from_access_token",
                return_value=mock_client,
            ) as client_factory,
        ):
            result = dependencies.get_calendar_client_for_slack_user("U123")

        assert result is mock_client
        client_factory.assert_called_once_with("linked-token")


class TestFastApiCalendarClientDependency:
    """Test FastAPI dependency provider behavior."""

    def test_google_provider_returns_google_client(self) -> None:
        """Return Google client without requiring a request token."""
        mock_client = Mock()
        request = Mock()

        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="google")),
            patch(
                "outlook_client_service.dependencies.get_google_calendar_client",
                return_value=mock_client,
            ),
        ):
            result = dependencies.get_calendar_client(
                request,
                client_factory=Mock(),
            )

        assert result is mock_client

    def test_invalid_provider_raises_http_exception(self) -> None:
        """Reject unsupported providers in the FastAPI dependency."""
        request = Mock()

        with (
            patch(
                "outlook_client_service.dependencies.settings",
                SettingsStub(calendar_provider="unknown"),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            dependencies.get_calendar_client(request, client_factory=Mock())

        assert exc_info.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert "Unsupported calendar provider" in str(exc_info.value.detail)

    def test_outlook_provider_builds_client_from_request_token(self) -> None:
        """Build Outlook client from the current request session token."""
        request = Mock()
        mock_graph_service = Mock()
        mock_calendar_client = Mock()
        client_factory = Mock(return_value=mock_calendar_client)

        with (
            patch("outlook_client_service.dependencies.settings", SettingsStub(calendar_provider="outlook")),
            patch(
                "outlook_client_service.dependencies.get_access_token",
                return_value="request-token",
            ) as access_token_getter,
            patch(
                "outlook_client_service.dependencies.get_graph_service_from_access_token",
                return_value=mock_graph_service,
            ) as graph_service_factory,
        ):
            result = dependencies.get_calendar_client(
                request,
                client_factory=client_factory,
            )

        assert result is mock_calendar_client
        access_token_getter.assert_called_once_with(request)
        graph_service_factory.assert_called_once_with("request-token")
        client_factory.assert_called_once_with(service=mock_graph_service)


class TestAccessTokenDependency:
    """Test access-token dependency error handling."""

    def test_get_access_token_wraps_unexpected_errors(self) -> None:
        """Convert unexpected auth failures into HTTP 401 responses."""
        request = Mock()

        with patch(
            "outlook_client_service.dependencies.get_valid_access_token",
            side_effect=RuntimeError("boom"),
        ), pytest.raises(HTTPException) as exc_info:
            dependencies.get_access_token(request)

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert "Authentication failed" in str(exc_info.value.detail)

    def test_get_access_token_reraises_http_exception(self) -> None:
        """Preserve HTTP exceptions raised by the auth layer."""
        request = Mock()
        original_exc = HTTPException(status_code=403, detail="forbidden")

        with patch(
            "outlook_client_service.dependencies.get_valid_access_token",
            side_effect=original_exc,
        ), pytest.raises(HTTPException) as exc_info:
            dependencies.get_access_token(request)

        assert exc_info.value is original_exc

    def test_get_access_token_returns_valid_token(self) -> None:
        """Return the token from the auth layer when available."""
        request = Mock()

        with patch(
            "outlook_client_service.dependencies.get_valid_access_token",
            return_value="valid-token",
        ):
            assert dependencies.get_access_token(request) == "valid-token"


class TestGraphServiceDependencies:
    """Test Graph service dependency helpers."""

    def test_get_graph_service_uses_current_request_token(self) -> None:
        """Build Graph service from the current request token."""
        request = Mock()
        mock_graph_service = Mock()

        with (
            patch(
                "outlook_client_service.dependencies.get_access_token",
                return_value="request-token",
            ) as access_token_getter,
            patch(
                "outlook_client_service.dependencies.AuthManager.get_graph_client_from_access_token",
                return_value=mock_graph_service,
            ) as graph_factory,
        ):
            result = dependencies.get_graph_service(request)

        assert result is mock_graph_service
        access_token_getter.assert_called_once_with(request)
        graph_factory.assert_called_once_with(
            access_token="request-token",
            scopes=SCOPES,
        )

    def test_get_graph_service_from_access_token_uses_auth_manager(self) -> None:
        """Build Graph service from an explicit access token."""
        mock_graph_service = Mock()

        with patch(
            "outlook_client_service.dependencies.AuthManager.get_graph_client_from_access_token",
            return_value=mock_graph_service,
        ) as graph_factory:
            result = dependencies.get_graph_service_from_access_token("token")

        assert result is mock_graph_service
        graph_factory.assert_called_once_with(
            access_token="token",
            scopes=SCOPES,
        )


def test_get_outlook_client_factory_returns_outlook_client() -> None:
    """Return the Outlook client factory."""
    assert dependencies.get_outlook_client_factory() is OutlookClient
