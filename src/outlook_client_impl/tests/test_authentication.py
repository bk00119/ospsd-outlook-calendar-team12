"""Unit tests for OutlookCalendarClient authentication and helper methods.

This module contains unit tests for the authentication flow and helper methods
of the OutlookCalendarClient class, mocking all external dependencies.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from outlook_client_impl.auth_manager import AuthManager


class TestAuthManagerInitAndCache:
    """Tests AuthManager initialization and cache persistence."""

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "read_text", return_value="CACHE_DATA")
    @patch.object(Path, "exists", return_value=True)
    def test_init_loads_cache_when_cache_file_exists(
            self,
            mock_exists: MagicMock,
            mock_read_text: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca: MagicMock,
    ) -> None:
        """Loads and deserializes MSAL cache when cache file exists."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        _ = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        fake_cache.deserialize.assert_called_once_with("CACHE_DATA")

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)  # cache file missing -> no deserialize
    def test_init_constructs_public_client_app_with_expected_args(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Constructs MSAL PublicClientApplication with expected args."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        client_id = "cid-123"
        authority = "https://login.microsoftonline.com/consumers"
        scopes = ["User.Read"]

        _ = AuthManager(
            client_id=client_id,
            authority=authority,
            scopes=scopes,
            auth_dir=Path(".auth"),
            interactive=False,
        )

        mock_pca_cls.assert_called_once_with(
            client_id=client_id,
            authority=authority,
            token_cache=fake_cache,
        )

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "write_text")
    @patch.object(Path, "mkdir")
    def test_save_cache_if_changed_does_not_write_when_state_unchanged(
            self,
            mock_mkdir: MagicMock,
            mock_write_text: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Does not write cache when MSAL reports no cache changes."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache
        mock_pca_cls.return_value = MagicMock()

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        auth._save_cache_if_changed()

        mock_mkdir.assert_not_called()
        mock_write_text.assert_not_called()

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "write_text")
    @patch.object(Path, "mkdir")
    def test_save_cache_if_changed_writes_when_state_changed(
            self,
            mock_mkdir: MagicMock,
            mock_write_text: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Writes cache to disk when MSAL reports cache changes."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = True
        fake_cache.serialize.return_value = "SERIALIZED_CACHE"
        mock_cache_cls.return_value = fake_cache
        mock_pca_cls.return_value = MagicMock()

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        auth._save_cache_if_changed()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write_text.assert_called_once_with("SERIALIZED_CACHE", encoding="utf-8")


class TestAuthManagerAccountPointer:
    """Tests account pointer load/save behavior."""

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)  # cache + account both treated as missing
    def test_load_saved_account_returns_none_when_account_file_missing(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Returns None when account pointer file is missing."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        assert auth._load_saved_account() is None

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "read_text")
    @patch.object(Path, "exists", autospec=True)
    def test_load_saved_account_returns_matching_account(
            self,
            mock_exists: MagicMock,
            mock_read_text: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Returns matching MSAL account using saved home_account_id pointer."""
        # If account.json exists AND cache does not exist, does _load_saved_account() return the correct account?

        # Arrange: cache object
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        # Arrange: MSAL app mock with accounts
        fake_app = MagicMock()
        matching = {"home_account_id": "X", "username": "x@example.com"}
        other = {"home_account_id": "Y", "username": "y@example.com"}
        fake_app.get_accounts.return_value = [other, matching]
        mock_pca_cls.return_value = fake_app

        # Arrange: only account.json exists
        def exists_side_effect(path: Path) -> bool:
            return str(path).endswith("account.json")

        mock_exists.side_effect = exists_side_effect

        # Arrange: account.json content includes home_account_id X
        mock_read_text.return_value = json.dumps({"home_account_id": "X"})

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        # Act
        got = auth._load_saved_account()

        # Assert
        assert got == matching

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "read_text")
    @patch.object(Path, "exists", autospec=True)
    def test_load_saved_account_returns_none_when_no_matching_account(
            self,
            mock_exists: MagicMock,
            mock_read_text: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Returns None when saved home_account_id does not match any cached account."""
        # Arrange: cache object
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        # Arrange: MSAL app mock with accounts that do NOT match X
        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [
            {"home_account_id": "Y", "username": "y@example.com"},
            {"home_account_id": "Z", "username": "z@example.com"},
        ]
        mock_pca_cls.return_value = fake_app

        # Arrange: only account.json exists
        def exists_side_effect(path: Path) -> bool:
            return str(path).endswith("account.json")

        mock_exists.side_effect = exists_side_effect

        # Arrange: account.json claims home_account_id X (but it won't match)
        mock_read_text.return_value = json.dumps({"home_account_id": "X"})

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        # Act / Assert
        assert auth._load_saved_account() is None

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "write_text")
    @patch.object(Path, "mkdir")
    def test_save_account_pointer_writes_first_account_when_accounts_exist(
            self,
            mock_mkdir: MagicMock,
            mock_write_text: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Writes the first cached MSAL account to the account pointer file."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        account1 = {"home_account_id": "A", "username": "a@example.com"}
        account2 = {"home_account_id": "B", "username": "b@example.com"}

        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [account1, account2]
        mock_pca_cls.return_value = fake_app

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        auth._save_account_pointer()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        written_text = mock_write_text.call_args.args[0]
        assert json.loads(written_text) == account1


class TestAuthManagerAcquireAccessToken:
    """Tests acquire_access_token decision logic."""

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_acquire_access_token_uses_silent_when_available(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Uses acquire_token_silent when available and does not invoke interactive."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [{"home_account_id": "X"}]
        fake_app.acquire_token_silent.return_value = {
            "access_token": "SILENT_TOKEN",
        }

        mock_pca_cls.return_value = fake_app

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        token = auth.acquire_access_token()

        assert token == "SILENT_TOKEN"

        fake_app.acquire_token_silent.assert_called_once()
        fake_app.acquire_token_interactive.assert_not_called()

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_acquire_access_token_falls_back_to_interactive_when_silent_fails(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Falls back to interactive auth when silent auth fails."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [{"home_account_id": "A"}]

        # Silent fails
        fake_app.acquire_token_silent.return_value = None

        # Interactive succeeds
        fake_app.acquire_token_interactive.return_value = {"access_token": "INTERACTIVE_TOKEN"}

        mock_pca_cls.return_value = fake_app

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        # Patch the persistence helpers so we can assert they were called
        with patch.object(auth, "_save_cache_if_changed") as mock_save_cache, \
                patch.object(auth, "_save_account_pointer") as mock_save_account:
            token = auth.acquire_access_token()

        assert token == "INTERACTIVE_TOKEN"
        fake_app.acquire_token_silent.assert_called_once()
        fake_app.acquire_token_interactive.assert_called_once()

        mock_save_cache.assert_called_once()
        mock_save_account.assert_called_once()

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_acquire_access_token_raises_when_interactive_fails(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Raises when both silent and interactive token acquisition fail."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [{"home_account_id": "A"}]

        # Silent fails
        fake_app.acquire_token_silent.return_value = None

        # Interactive fails (MSAL returns an error payload, no access_token)
        fake_app.acquire_token_interactive.return_value = {
            "error": "access_denied",
            "error_description": "User cancelled the flow",
        }

        mock_pca_cls.return_value = fake_app

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        with pytest.raises(RuntimeError):
            auth.acquire_access_token()

        fake_app.acquire_token_silent.assert_called_once()
        fake_app.acquire_token_interactive.assert_called_once()

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_acquire_access_token_interactive_true_skips_silent(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Forces interactive auth when interactive flag is True."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [{"home_account_id": "A"}]

        # Even if silent would succeed, it must NOT be called when interactive=True
        fake_app.acquire_token_silent.return_value = {"access_token": "SILENT_TOKEN"}

        # Interactive succeeds
        fake_app.acquire_token_interactive.return_value = {"access_token": "INTERACTIVE_TOKEN"}

        mock_pca_cls.return_value = fake_app

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=True,
        )

        token = auth.acquire_access_token()

        assert token == "INTERACTIVE_TOKEN"
        fake_app.acquire_token_silent.assert_not_called()
        fake_app.acquire_token_interactive.assert_called_once()

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_acquire_access_token_interactive_true_persists_on_success(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Persists cache and account pointer after successful interactive auth."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache

        fake_app = MagicMock()
        fake_app.get_accounts.return_value = [{"home_account_id": "A"}]
        fake_app.acquire_token_interactive.return_value = {"access_token": "INTERACTIVE_TOKEN"}
        mock_pca_cls.return_value = fake_app

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=True,
        )

        with patch.object(auth, "_save_cache_if_changed") as mock_save_cache, \
                patch.object(auth, "_save_account_pointer") as mock_save_account:
            token = auth.acquire_access_token()

        assert token == "INTERACTIVE_TOKEN"
        fake_app.acquire_token_silent.assert_not_called()
        fake_app.acquire_token_interactive.assert_called_once()

        mock_save_cache.assert_called_once()
        mock_save_account.assert_called_once()


class TestAuthManagerCredentialAdapter:
    """Tests the TokenCredential adapter used by the Graph SDK."""

    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_credential_get_token_uses_passed_scopes(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
    ) -> None:
        """Credential forwards explicit scopes to AuthManager token acquisition."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache
        mock_pca_cls.return_value = MagicMock()

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["DEFAULT_SCOPE"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        # Make sure we can observe what scopes were forwarded
        with patch.object(auth, "acquire_access_token", return_value="TOKEN") as mock_acquire:
            cred = auth.get_credential()

            token_obj = cred.get_token("ScopeA", "ScopeB")

        mock_acquire.assert_called_once_with(["ScopeA", "ScopeB"])
        assert token_obj.token == "TOKEN"

    @patch("outlook_client_impl.auth_manager.time.time", return_value=1_700_000_000)
    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_credential_get_token_sets_expires_on_about_one_hour(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
            mock_time: MagicMock,
    ) -> None:
        """Credential sets expires_on to now + 3600 seconds."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache
        mock_pca_cls.return_value = MagicMock()

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        with patch.object(auth, "acquire_access_token", return_value="TOKEN"):
            cred = auth.get_credential()
            token_obj = cred.get_token("User.Read")

        assert token_obj.token == "TOKEN"
        assert token_obj.expires_on == 1_700_000_000 + 3600


class TestAuthManagerGraphClientWiring:
    """Tests GraphServiceClient construction and wiring."""

    @patch("outlook_client_impl.auth_manager.GraphServiceClient")
    @patch("outlook_client_impl.auth_manager.msal.PublicClientApplication")
    @patch("outlook_client_impl.auth_manager.msal.SerializableTokenCache")
    @patch.object(Path, "exists", return_value=False)
    def test_get_graph_client_constructs_client_with_credential_and_scopes(
            self,
            mock_exists: MagicMock,
            mock_cache_cls: MagicMock,
            mock_pca_cls: MagicMock,
            mock_graph_cls: MagicMock,
    ) -> None:
        """Constructs GraphServiceClient with AuthManager credential and scopes."""
        fake_cache = MagicMock()
        fake_cache.has_state_changed = False
        mock_cache_cls.return_value = fake_cache
        mock_pca_cls.return_value = MagicMock()

        auth = AuthManager(
            client_id="cid",
            authority="https://login.microsoftonline.com/consumers",
            scopes=["User.Read", "Calendars.ReadWrite"],
            auth_dir=Path(".auth"),
            interactive=False,
        )

        # Mock get_credential to ensure it's used
        with patch.object(auth, "get_credential", return_value="FAKE_CRED") as mock_get_cred:
            auth.get_graph_client()

        mock_get_cred.assert_called_once()

        mock_graph_cls.assert_called_once_with(
            credentials="FAKE_CRED",
            scopes=["User.Read", "Calendars.ReadWrite"],
        )
