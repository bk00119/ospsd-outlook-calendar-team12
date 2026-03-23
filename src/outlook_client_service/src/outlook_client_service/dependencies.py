"""Dependency providers for the Outlook client service."""

from fastapi import HTTPException, Request
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


def get_outlook_client(request: Request) -> OutlookClient:
    """Create an OutlookClient backed by the current session access token."""
    access_token = get_access_token(request)
    graph_service = AuthManager.get_graph_client_from_access_token(
        access_token=access_token,
        scopes=SCOPES,
    )
    return OutlookClient(service=graph_service)
