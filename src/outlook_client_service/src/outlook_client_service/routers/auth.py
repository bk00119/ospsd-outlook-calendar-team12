"""Authentication routes for the Outlook client service."""

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


@router.get("/login")
def login() -> RedirectResponse:
    """Redirect the user to Microsoft's authorization page."""
    if not settings.azure_client_id:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="AZURE_CLIENT_ID is not configured.")

    params = {
        "client_id": settings.azure_client_id,
        "response_type": "code",
        "redirect_uri": settings.azure_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
    }

    auth_url = f"{settings.azure_authority}/oauth2/v2.0/authorize?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    """Clear the current session."""
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
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
) -> dict[str, str]:
    """Handle the OAuth callback from Microsoft."""
    if error:
        detail = error_description or error
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=detail)

    if not code:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Missing authorization code.")

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
    return {"message": "Authentication successful."}
