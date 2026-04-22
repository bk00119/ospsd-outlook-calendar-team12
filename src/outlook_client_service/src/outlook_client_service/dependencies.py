"""Dependency providers for the Outlook client service."""

from collections.abc import Callable
from typing import Annotated

from calendar_client_api.client import Client as CalendarClient
from fastapi import Depends, HTTPException, Request
from outlook_client_impl.auth_manager import AuthManager
from outlook_client_impl.outlook_impl import OutlookClient

from outlook_client_service.routers.auth import SCOPES, get_valid_access_token


def get_access_token(request: Request) -> str:
    """Return a valid access token from the session."""
    try:
        return get_valid_access_token(request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}") from exc


def get_graph_service(request: Request) -> object:
    """Return a Graph client built from the current session access token."""
    access_token = get_access_token(request)
    return AuthManager.get_graph_client_from_access_token(
        access_token=access_token,
        scopes=SCOPES,
    )

def get_outlook_client_factory() -> Callable[..., CalendarClient]:
    """Return the concrete Outlook client implementation factory."""
    return OutlookClient

def get_calendar_client(
    graph_service: Annotated[object, Depends(get_graph_service)],
    client_factory: Annotated[
        Callable[..., CalendarClient],
        Depends(get_outlook_client_factory),
    ],
) -> CalendarClient:
    """Create an Outlook client through the interface-backed DI provider."""
    return client_factory(service=graph_service)

