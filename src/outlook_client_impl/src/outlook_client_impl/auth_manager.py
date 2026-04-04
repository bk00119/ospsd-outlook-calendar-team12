"""Authentication utilities for Microsoft Graph (Outlook Calendar).

This module provides an MSAL-backed `AuthManager` that supports:
- Interactive auth (browser)
- Silent auth via a serialized token cache on disk
- Creating a `GraphServiceClient` using an `azure.core.credentials.TokenCredential` adapter
- Creating a `GraphServiceClient` from an already-acquired access token

The cache files under `.auth/` contain sensitive tokens and must not be committed.
"""

import json
import time
from pathlib import Path
from typing import Any, cast

import msal  # type: ignore[import-untyped]
from azure.core.credentials import AccessToken, TokenCredential
from msgraph.graph_service_client import GraphServiceClient


# --- AuthManager class providing MSAL + Graph integration ---
class AuthManager:
    """MSAL-based auth manager with:

    - Plain-file token cache: .auth/msal_cache.json
    - Plain-file account pointer: .auth/account.json
    - silent-first auth with interactive fallback (or forced interactive)

    Use `get_graph_client()` to obtain an authenticated GraphServiceClient.
    """

    AUTH_DIR = Path(".auth")
    CACHE_PATH = AUTH_DIR / "msal_cache.json"
    ACCOUNT_PATH = AUTH_DIR / "account.json"

    def __init__(
        self,
        client_id: str,
        authority: str,
        scopes: list[str],
        auth_dir: Path = AUTH_DIR,
        *,
        interactive: bool = False,
    ) -> None:
        """Create a new AuthManager.

        Parameters
        ----------
        client_id:
            Entra application (client) ID.
        authority:
            OAuth authority URL, e.g. `https://login.microsoftonline.com/consumers`.
        scopes:
            Delegated Microsoft Graph scopes (e.g., `User.Read`, `Calendars.ReadWrite`).
        auth_dir:
            Directory used to persist the MSAL token cache and account pointer.
        interactive:
            If True, always allow an interactive browser prompt when a token is needed.
            If False, prefer silent auth and only fall back to interactive when required.

        """
        self.client_id = client_id
        self.authority = authority
        self.scopes = scopes
        self.auth_dir = auth_dir
        self.cache_path = self.CACHE_PATH
        self.account_path = self.ACCOUNT_PATH
        self.interactive = interactive

        self._cache = msal.SerializableTokenCache()
        if self.cache_path.exists():
            self._cache.deserialize(self.cache_path.read_text(encoding="utf-8"))

        self._app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            token_cache=self._cache,
        )

    def _save_cache_if_changed(self) -> None:
        """Persist the serialized MSAL token cache to disk if it changed."""
        if self._cache.has_state_changed:
            self.auth_dir.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(self._cache.serialize(), encoding="utf-8")

    def _load_saved_account(self) -> dict[str, Any] | None:
        """Load the previously-selected MSAL account, if available.

        Returns
        -------
        dict | None
            An MSAL account dict (matching `home_account_id`) or None if not found.

        """
        if not self.account_path.exists():
            return None
        try:
            acct_json = json.loads(self.account_path.read_text(encoding="utf-8"))
            haid = acct_json.get("home_account_id")
            if not haid:
                return None
            for a in self._app.get_accounts():
                if a.get("home_account_id") == haid:
                    return cast("dict[str, Any]", a)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return None

    def _save_account_pointer(self) -> None:
        """Save a pointer to the currently active account.

        This stores a small JSON object (including `home_account_id`) so future runs
        can target the same user account for silent token acquisition.
        """
        accounts = self._app.get_accounts()
        picked = accounts[0] if accounts else {}
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self.account_path.write_text(json.dumps(picked, indent=2), encoding="utf-8")

    def acquire_access_token(self, scopes: list[str] | None = None) -> str:
        """Acquire an access token for Microsoft Graph.

        Attempts silent acquisition first (when interactive is not forced). If silent
        acquisition fails, falls back to an interactive browser prompt.

        Parameters
        ----------
        scopes:
            Optional override scope list. If omitted, uses `self.scopes`.

        Returns
        -------
        str
            A bearer access token string.

        """
        req_scopes = scopes or self.scopes

        result: dict[str, Any] | None = None

        if not self.interactive:
            account = self._load_saved_account()
            if account is None:
                accounts = self._app.get_accounts()
                account = accounts[0] if accounts else None
            if account is not None:
                result = self._app.acquire_token_silent(req_scopes, account=account)

        if not result or "access_token" not in result:
            # interactive fallback (or forced interactive)
            result = self._app.acquire_token_interactive(
                scopes=req_scopes,
                prompt="select_account",
            )
            if "access_token" not in result:
                msg = f"MSAL auth failed: {result}"
                raise RuntimeError(msg)
            # Persist after interactive
            self._save_cache_if_changed()
            self._save_account_pointer()
        else:
            # Silent succeeded; cache may still change (rotation/refresh)
            self._save_cache_if_changed()

        return cast("str", result["access_token"])

    class _MsalCredential(TokenCredential):
        """Adapter so GraphServiceClient can use MSAL via TokenCredential."""

        def __init__(self, manager: "AuthManager") -> None:
            self._m = manager

        def get_token(
            self,
            *scopes: str,
            **kwargs: object,
        ) -> AccessToken:
            """Return an AccessToken for the requested scopes.

            The Graph SDK calls this to obtain a bearer token. We delegate to MSAL via
            `AuthManager.acquire_access_token`.
            """
            _ = kwargs  # explicitly mark as used
            req_scopes = list(scopes) if scopes else self._m.scopes
            token_str = self._m.acquire_access_token(req_scopes)
            # expires_in is not easily available here without returning the whole dict.
            # Using ~1h default is fine; Graph SDK will call again when needed.
            expires_on = int(time.time()) + 3600
            return AccessToken(token_str, expires_on)

    class _StaticAccessTokenCredential(TokenCredential):
        """TokenCredential backed by an already-acquired access token."""

        def __init__(self, access_token: str, expires_on: int | None = None) -> None:
            self._access_token = access_token
            self._expires_on = expires_on or (int(time.time()) + 3600)

        def get_token(
            self,
            *scopes: str,
            **kwargs: object,
        ) -> AccessToken:
            """Return the stored access token as an AccessToken instance."""
            _ = scopes
            _ = kwargs
            return AccessToken(self._access_token, self._expires_on)

    def get_credential(self) -> TokenCredential:
        """Return a TokenCredential adapter backed by this AuthManager."""
        return AuthManager._MsalCredential(self)

    def get_graph_client(self) -> GraphServiceClient:
        """Create an authenticated GraphServiceClient using the MSAL-backed credential."""
        return GraphServiceClient(credentials=self.get_credential(), scopes=self.scopes)

    @classmethod
    def get_graph_client_from_access_token(
        cls,
        access_token: str,
        scopes: list[str],
        *,
        expires_on: int | None = None,
    ) -> GraphServiceClient:
        """Create a GraphServiceClient from an already-acquired access token."""
        credential = cls._StaticAccessTokenCredential(
            access_token=access_token,
            expires_on=expires_on,
        )
        return GraphServiceClient(credentials=credential, scopes=scopes)
