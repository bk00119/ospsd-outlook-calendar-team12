"""Tests for runtime chat implementation loading."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from chat_client_api.client import Channel, ChatClient, Message, _ClientRegistry, register_client
from outlook_client_service.chat_registry import CHAT_CLIENT_IMPL_MODULE_ENV, get_registered_chat_client


class _RegistryChatClient(ChatClient):
    """Minimal chat client used to verify registry loading."""

    def send_message(self, channel_id: str, text: str) -> Message:
        """Return a fake sent message."""
        return Message(
            message_id="msg-1",
            channel=channel_id,
            text=text,
            sender="bot",
            timestamp=datetime(2026, 5, 13, tzinfo=UTC),
        )

    def get_channels(self) -> list[Channel]:
        """Return no channels."""
        return []

    def get_channel(self, channel_id: str) -> Channel:
        """Not needed for this test client."""
        raise NotImplementedError

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        """Return no messages."""
        return []

    def get_message(self, message_id: str) -> Message:
        """Not needed for this test client."""
        raise NotImplementedError

    def delete_message(self, message_id: str) -> None:
        """Not needed for this test client."""
        raise NotImplementedError


@pytest.fixture(autouse=True)
def restore_chat_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep shared chat registry state isolated across tests."""
    original_factory = _ClientRegistry.get()
    monkeypatch.setattr(_ClientRegistry, "_factory", original_factory)
    monkeypatch.delenv(CHAT_CLIENT_IMPL_MODULE_ENV, raising=False)


def test_get_registered_chat_client_returns_existing_registration() -> None:
    """Return the existing registered implementation without importing a module."""
    register_client(_RegistryChatClient)

    assert isinstance(get_registered_chat_client(), _RegistryChatClient)


def test_get_registered_chat_client_imports_env_configured_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Import CHAT_CLIENT_IMPL_MODULE to let the implementation self-register."""
    module_name = "test_dynamic_chat_impl"

    def fake_import_module(name: str) -> object:
        assert name == module_name
        register_client(_RegistryChatClient)
        return object()

    monkeypatch.setattr(_ClientRegistry, "_factory", None)
    monkeypatch.setattr("outlook_client_service.chat_registry.importlib.import_module", fake_import_module)
    monkeypatch.setenv(CHAT_CLIENT_IMPL_MODULE_ENV, module_name)

    assert isinstance(get_registered_chat_client(), _RegistryChatClient)


def test_get_registered_chat_client_raises_without_module() -> None:
    """Raise a clear error when no implementation is registered or configured."""
    _ClientRegistry._factory = None

    with pytest.raises(RuntimeError, match=CHAT_CLIENT_IMPL_MODULE_ENV):
        get_registered_chat_client()
