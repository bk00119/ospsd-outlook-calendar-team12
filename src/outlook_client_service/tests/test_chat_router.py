from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from chat_client_api import ChatClient
from chat_client_api.client import Channel, Message
from fastapi.testclient import TestClient


class _MockChatClient(ChatClient):  # type: ignore[misc]  # ChatClient is untyped (no py.typed in chat_client_api); subclassing Any is safe here
    """In-memory ChatClient for integration tests — records sent messages."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_message(self, channel_id: str, text: str) -> Message:
        self.sent.append((channel_id, text))
        return Message(
            message_id="mock-msg-id",
            channel=channel_id,
            text=text,
            sender="bot",
            timestamp="2026-04-22T00:00:00Z",
        )

    def get_channels(self) -> list[Channel]:
        return []

    def get_channel(self, channel_id: str) -> Channel:
        raise NotImplementedError

    def get_messages(
        self, channel_id: str, limit: int, cursor: str | None = None,
    ) -> list[Message]:
        return []

    def get_message(self, message_id: str) -> Message:
        raise NotImplementedError

    def delete_message(self, message_id: str) -> None:
        raise NotImplementedError


def _make_client(
    ai_response: str,
    mock_chat: _MockChatClient,
) -> TestClient:
    """Build a TestClient with mocked AI service and chat client."""
    from outlook_client_service.main import create_app
    from outlook_client_service.routers.chat import get_chat_client, get_intelligent_app

    mock_service = MagicMock()
    mock_service.process_chat.return_value = ai_response

    app = create_app()
    app.dependency_overrides[get_intelligent_app] = lambda: mock_service
    app.dependency_overrides[get_chat_client] = lambda: mock_chat
    return TestClient(app)


@pytest.mark.integration
def test_chat_returns_ai_response() -> None:
    """POST /chat/ should return the AI-generated response in the body."""
    mock_chat = _MockChatClient()
    http = _make_client("You have 2 meetings tomorrow.", mock_chat)

    response = http.post(
        "/chat/",
        json={
            "message": "What meetings do I have tomorrow?",
            "channel_id": "C1234567",
            "timezone": "America/New_York",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["response"] == "You have 2 meetings tomorrow."


@pytest.mark.integration
def test_chat_sends_message_to_channel() -> None:
    """POST /chat/ should forward the AI response to the specified channel."""
    mock_chat = _MockChatClient()
    http = _make_client("Event created: Team sync at 3pm.", mock_chat)

    http.post(
        "/chat/",
        json={
            "message": "Schedule a team sync tomorrow at 3pm",
            "channel_id": "C9999",
            "timezone": "UTC",
        },
    )

    assert len(mock_chat.sent) == 1
    channel_id, text = mock_chat.sent[0]
    assert channel_id == "C9999"
    assert text == "Event created: Team sync at 3pm."


@pytest.mark.integration
def test_chat_passes_timezone_to_service() -> None:
    """POST /chat/ should forward the user's timezone to the AI service."""
    from outlook_client_service.main import create_app
    from outlook_client_service.routers.chat import get_chat_client, get_intelligent_app

    mock_service = MagicMock()
    mock_service.process_chat.return_value = "Done."
    mock_chat = _MockChatClient()

    app = create_app()
    app.dependency_overrides[get_intelligent_app] = lambda: mock_service
    app.dependency_overrides[get_chat_client] = lambda: mock_chat

    TestClient(app).post(
        "/chat/",
        json={
            "message": "Schedule lunch at noon",
            "channel_id": "C0001",
            "timezone": "America/Chicago",
        },
    )

    mock_service.process_chat.assert_called_once_with(
        "Schedule lunch at noon", "America/Chicago",
    )
