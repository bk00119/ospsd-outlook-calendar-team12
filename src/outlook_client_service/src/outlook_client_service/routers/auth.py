"""Authentication routes for the Outlook client service."""

import secrets
import time
from http import HTTPStatus
from typing import Annotated
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from outlook_client_service.config import settings

SCOPES = [
    "offline_access",
    "https://graph.microsoft.com/Calendars.ReadWrite",
]
SLACK_AUTH_QUERY_PARAM = "slack_auth_token"
SESSION_OAUTH_STATE = "oauth_state"
SESSION_SLACK_USER_ID = "slack_user_id"
_SESSION_TOKEN_KEYS = (
    "access_token",
    "refresh_token",
    "expires_in",
    "expires_at",
)

_slack_user_token_store: dict[str, dict[str, object]] = {}
_pending_slack_auth_tokens: dict[str, str] = {}

router = APIRouter()


def _store_token_data(request: Request, token_data: dict[str, object]) -> None:
    """Store token data in the current session."""
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Missing access token in token response.")

    request.session["access_token"] = access_token

    refresh_token = token_data.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        request.session["refresh_token"] = refresh_token

    expires_in = token_data.get("expires_in")
    if isinstance(expires_in, int):
        request.session["expires_in"] = expires_in
        request.session["expires_at"] = int(time.time()) + expires_in


def _current_session_token_data(request: Request) -> dict[str, object]:
    """Return token data currently stored in the session."""
    return {
        key: value
        for key in _SESSION_TOKEN_KEYS
        if (value := request.session.get(key)) is not None
    }


def bind_slack_user_to_current_session(request: Request) -> None:
    """Bind the current authenticated calendar session to a Slack user."""
    slack_user_id = request.session.get(SESSION_SLACK_USER_ID)
    if not isinstance(slack_user_id, str) or not slack_user_id:
        return

    token_data = _current_session_token_data(request)
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        return

    _slack_user_token_store[slack_user_id] = token_data


def get_slack_user_token_data(slack_user_id: str) -> dict[str, object] | None:
    """Return stored token data for a Slack user, if available."""
    return _slack_user_token_store.get(slack_user_id)


def create_slack_auth_token(slack_user_id: str) -> str:
    """Create a short-lived auth token for linking a Slack user."""
    token = secrets.token_urlsafe(32)
    _pending_slack_auth_tokens[token] = slack_user_id
    return token


def _resolve_slack_auth_token(slack_auth_token: str) -> str:
    """Resolve a Slack auth token to a Slack user ID"""
    slack_user_id = _pending_slack_auth_tokens.pop(slack_auth_token, None)
    if not slack_user_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Invalid or expired Slack authentication token.",
        )
    return slack_user_id


def _create_oauth_state(request: Request) -> str:
    """Create and store an OAuth state value for CSRF protection."""
    state = secrets.token_urlsafe(32)
    request.session[SESSION_OAUTH_STATE] = state
    return state


def _verify_oauth_state(request: Request, state: str | None) -> None:
    """Validate the OAuth state value returned by the provider."""
    expected_state = request.session.pop(SESSION_OAUTH_STATE, None)
    if not isinstance(expected_state, str) or state != expected_state:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Invalid OAuth state",
        )


@router.get("/login")
def login(
    request: Request,
    slack_auth_token: Annotated[str | None, Query(alias=SLACK_AUTH_QUERY_PARAM)] = None,
) -> RedirectResponse:
    """Redirect the user to Microsoft's authorization page."""
    if slack_auth_token:
        request.session[SESSION_SLACK_USER_ID] = _resolve_slack_auth_token(slack_auth_token)

    if not settings.azure_client_id:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="AZURE_CLIENT_ID is not configured.")

    params = {
        "client_id": settings.azure_client_id,
        "response_type": "code",
        "redirect_uri": settings.azure_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": _create_oauth_state(request),
    }

    auth_url = f"{settings.azure_authority}/oauth2/v2.0/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    """Clear the current session."""
    slack_user_id = request.session.get(SESSION_SLACK_USER_ID)
    if isinstance(slack_user_id, str):
        _slack_user_token_store.pop(slack_user_id, None)

    request.session.clear()
    return {"message": "Logged out successfully."}


def refresh_access_token(request: Request) -> str:
    """Refresh the current access token using the session refresh token."""
    refresh_token = request.session.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Missing refresh token. Please log in again.")

    token_url = f"{settings.azure_authority}/oauth2/v2.0/token"
    data = {
        "client_id": settings.azure_client_id,
        "client_secret": settings.azure_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": settings.azure_redirect_uri,
        "scope": " ".join(SCOPES),
    }

    response = requests.post(token_url, data=data, timeout=10)
    token_data = response.json()
    if response.status_code != HTTPStatus.OK:
        request.session.clear()
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Failed to refresh token. Please log in again.")

    _store_token_data(request, token_data)
    stored_access_token = request.session.get("access_token")
    if not isinstance(stored_access_token, str) or not stored_access_token:
        message = "Missing access token in session after refresh."
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=message)
    return stored_access_token


def _refresh_slack_user_token_data(slack_user_id: str, token_data: dict[str, object]) -> str | None:
    """Refresh and store token data for a Slack-linked calendar session."""
    refresh_token = token_data.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        _slack_user_token_store.pop(slack_user_id, None)
        return None

    token_url = f"{settings.azure_authority}/oauth2/v2.0/token"
    data = {
        "client_id": settings.azure_client_id,
        "client_secret": settings.azure_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": settings.azure_redirect_uri,
        "scope": " ".join(SCOPES),
    }

    response = requests.post(token_url, data=data, timeout=10)
    refreshed_token_data = response.json()
    if response.status_code != HTTPStatus.OK:
        _slack_user_token_store.pop(slack_user_id, None)
        return None

    access_token = refreshed_token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        _slack_user_token_store.pop(slack_user_id, None)
        return None

    new_token_data = dict(token_data)
    new_token_data["access_token"] = access_token

    new_refresh_token = refreshed_token_data.get("refresh_token")
    if isinstance(new_refresh_token, str) and new_refresh_token:
        new_token_data["refresh_token"] = new_refresh_token

    expires_in = refreshed_token_data.get("expires_in")
    if isinstance(expires_in, int):
        new_token_data["expires_in"] = expires_in
        new_token_data["expires_at"] = int(time.time()) + expires_in

    _slack_user_token_store[slack_user_id] = new_token_data
    return access_token


def get_valid_access_token_for_slack_user(
    slack_user_id: str,
    refresh_buffer_seconds: int = 60,
) -> str | None:
    """Return a valid access token for a Slack-linked calendar session."""
    token_data = get_slack_user_token_data(slack_user_id)
    if token_data is None:
        return None

    access_token = token_data.get("access_token")
    expires_at = token_data.get("expires_at")
    now = int(time.time())

    if isinstance(access_token, str) and access_token:
        if isinstance(expires_at, int) and now < expires_at - refresh_buffer_seconds:
            return access_token
        return _refresh_slack_user_token_data(slack_user_id, token_data)

    return _refresh_slack_user_token_data(slack_user_id, token_data)


def get_valid_access_token(request: Request, refresh_buffer_seconds: int = 60) -> str:
    """Return a valid access token, refreshing it if it is missing or near expiry."""
    access_token = request.session.get("access_token")
    expires_at = request.session.get("expires_at")
    now = int(time.time())

    if isinstance(access_token, str) and access_token:
        if isinstance(expires_at, int) and now < expires_at - refresh_buffer_seconds:
            return access_token
        return refresh_access_token(request)

    return refresh_access_token(request)


@router.get("/callback")
def callback(
    request: Request,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
) -> dict[str, str]:
    """Handle the OAuth callback from Microsoft."""
    if error:
        detail = error_description or error
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=detail)

    if not code:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Missing authorization code.")

    _verify_oauth_state(request, state)

    token_url = f"{settings.azure_authority}/oauth2/v2.0/token"

    data = {
        "client_id": settings.azure_client_id,
        "client_secret": settings.azure_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.azure_redirect_uri,
        "scope": " ".join(SCOPES),
    }

    response = requests.post(token_url, data=data, timeout=10)
    token_data = response.json()
    if response.status_code != HTTPStatus.OK:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=token_data)
    _store_token_data(request, token_data)
    bind_slack_user_to_current_session(request)
    return {"message": "Authentication successful."}
