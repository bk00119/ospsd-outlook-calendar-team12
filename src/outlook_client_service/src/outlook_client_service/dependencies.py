"""Dependency providers for the Outlook client service."""

from collections.abc import Callable
from typing import Annotated

from calendar_client_api.client import Client as CalendarClient
from fastapi import Depends, HTTPException, Request
from msgraph.graph_service_client import GraphServiceClient
from outlook_client_impl.auth_manager import AuthManager
from outlook_client_impl.outlook_impl import OutlookClient

from outlook_client_service.config import settings
from outlook_client_service.google_calendar_client import GoogleCalendarClient
from outlook_client_service.routers.auth import SCOPES, get_valid_access_token, get_valid_access_token_for_slack_user

OUTLOOK_PROVIDER = "outlook"
GOOGLE_PROVIDER = "google"


def get_calendar_provider() -> str:
    """Return the configured calendar provider name."""
    return settings.calendar_provider


def get_google_calendar_client() -> CalendarClient:
    """Create a Google Calendar client through the shared calendar interface."""
    return GoogleCalendarClient(
        credentials_file=settings.google_credentials_file,
        token_file=settings.google_token_file,
        calendar_id=settings.google_calendar_id,
        interactive=settings.google_interactive_auth,
    )


def get_access_token(request: Request) -> str:
    """Return a valid access token from the session."""
    try:
        return get_valid_access_token(request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}") from exc


def get_graph_service(request: Request) -> GraphServiceClient:
    """Return a Graph client built from the current session access token."""
    access_token = get_access_token(request)
    return AuthManager.get_graph_client_from_access_token(
        access_token=access_token,
        scopes=SCOPES,
    )


def get_graph_service_from_access_token(access_token: str) -> GraphServiceClient:
    """Return a Graph client built from an explicit access token."""
    return AuthManager.get_graph_client_from_access_token(
        access_token=access_token,
        scopes=SCOPES,
    )


def get_calendar_client_from_access_token(
    access_token: str,
    client_factory: Callable[..., CalendarClient] = OutlookClient,
) -> CalendarClient:
    """Create a calendar client from an explicit access token."""
    provider = get_calendar_provider()
    if provider == GOOGLE_PROVIDER:
        return get_google_calendar_client()
    if provider != OUTLOOK_PROVIDER:
        message = f"Unsupported calendar provider: {provider}"
        raise ValueError(message)

    graph_service = get_graph_service_from_access_token(access_token)
    return client_factory(service=graph_service)


def get_calendar_client_for_slack_user(slack_user_id: str) -> CalendarClient | None:
    """Return a calendar client for a linked Slack user, if available."""
    provider = get_calendar_provider()
    if provider == GOOGLE_PROVIDER:
        return get_google_calendar_client()
    if provider != OUTLOOK_PROVIDER:
        message = f"Unsupported calendar provider: {provider}"
        raise ValueError(message)

    access_token = get_valid_access_token_for_slack_user(slack_user_id)
    if access_token is None:
        return None

    return get_calendar_client_from_access_token(access_token)


def get_outlook_client_factory() -> Callable[..., CalendarClient]:
    """Return the concrete Outlook client implementation factory."""
    return OutlookClient


def get_calendar_client(
    request: Request,
    client_factory: Annotated[
        Callable[..., CalendarClient],
        Depends(get_outlook_client_factory),
    ],
) -> CalendarClient:
    """Create a calendar client through the configured provider."""
    provider = get_calendar_provider()
    if provider == GOOGLE_PROVIDER:
        return get_google_calendar_client()
    if provider != OUTLOOK_PROVIDER:
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported calendar provider: {provider}",
        )

    access_token = get_access_token(request)
    graph_service = get_graph_service_from_access_token(access_token)
    return client_factory(service=graph_service)
