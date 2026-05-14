"""Tests for the Team 12 Slack chat adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from chat_client_api.client import ChannelNotFoundError, MessageDeleteError, MessageNotFoundError
from outlook_client_service.slack_chat_client import (
    SLACK_BOT_TOKEN_ENV,
    Team12SlackClient,
    _decode_message_id,
    create_slack_chat_client,
)


class FakeSlackWebClient:
    """Fake Slack SDK client with programmable responses."""

    def __init__(self) -> None:
        """Initialize recorded calls and default responses."""
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.post_response: dict[str, Any] = {
            "ok": True,
            "channel": "C123",
            "ts": "1770000000.000001",
            "bot_id": "B123",
            "message": {"text": "hello"},
        }
        self.channels_response: dict[str, Any] = {
            "ok": True,
            "channels": [{"id": "C123", "name": "calendar", "is_private": False}],
            "response_metadata": {"next_cursor": ""},
        }
        self.info_response: dict[str, Any] = {
            "ok": True,
            "channel": {"id": "C123", "name": "calendar", "is_private": False},
        }
        self.history_response: dict[str, Any] = {
            "ok": True,
            "messages": [
                {
                    "ts": "1770000000.000001",
                    "text": "hi",
                    "user": "U123",
                },
            ],
        }
        self.delete_response: dict[str, Any] = {"ok": True}

    def chat_postMessage(self, *, channel: str, text: str) -> dict[str, Any]:  # noqa: N802
        """Record and return a fake post response."""
        self.calls.append(("chat_postMessage", {"channel": channel, "text": text}))
        return self.post_response

    def conversations_list(self, **kwargs: object) -> dict[str, Any]:
        """Record and return fake channel list response."""
        self.calls.append(("conversations_list", kwargs))
        return self.channels_response

    def conversations_info(self, *, channel: str) -> dict[str, Any]:
        """Record and return fake channel info response."""
        self.calls.append(("conversations_info", {"channel": channel}))
        return self.info_response

    def conversations_history(self, **kwargs: object) -> dict[str, Any]:
        """Record and return fake history response."""
        self.calls.append(("conversations_history", kwargs))
        return self.history_response

    def chat_delete(self, *, channel: str, ts: str) -> dict[str, Any]:
        """Record and return fake delete response."""
        self.calls.append(("chat_delete", {"channel": channel, "ts": ts}))
        return self.delete_response


def test_send_message_maps_slack_response() -> None:
    """Map Slack post response into the shared Message model."""
    fake = FakeSlackWebClient()
    client = Team12SlackClient(token="xoxb-test", web_client=fake)

    message = client.send_message("C123", "hello")

    assert message.message_id == "C123:1770000000.000001"
    assert message.channel == "C123"
    assert message.text == "hello"
    assert message.sender == "B123"
    assert message.timestamp == datetime.fromtimestamp(1770000000.000001, tz=UTC)
    assert fake.calls == [("chat_postMessage", {"channel": "C123", "text": "hello"})]


def test_get_channels_maps_slack_response() -> None:
    """Map Slack channel list response into shared channels."""
    client = Team12SlackClient(token="xoxb-test", web_client=FakeSlackWebClient())

    channels = client.get_channels()

    assert channels[0].channel_id == "C123"
    assert channels[0].name == "calendar"
    assert channels[0].is_private is False


def test_get_channel_raises_when_response_has_no_channel() -> None:
    """Raise a shared ChannelNotFoundError for missing Slack channel payloads."""
    fake = FakeSlackWebClient()
    fake.info_response = {"ok": True}
    client = Team12SlackClient(token="xoxb-test", web_client=fake)

    with pytest.raises(ChannelNotFoundError):
        client.get_channel("C404")


def test_get_messages_maps_slack_history() -> None:
    """Map Slack history response into shared messages."""
    client = Team12SlackClient(token="xoxb-test", web_client=FakeSlackWebClient())

    messages = client.get_messages("C123", limit=5)

    assert messages[0].message_id == "C123:1770000000.000001"
    assert messages[0].text == "hi"
    assert messages[0].sender == "U123"


def test_get_message_raises_when_history_is_empty() -> None:
    """Raise a shared MessageNotFoundError when Slack returns no messages."""
    fake = FakeSlackWebClient()
    fake.history_response = {"ok": True, "messages": []}
    client = Team12SlackClient(token="xoxb-test", web_client=fake)

    with pytest.raises(MessageNotFoundError):
        client.get_message("C123:1770000000.000001")


def test_delete_message_calls_slack_delete() -> None:
    """Decode shared message ID and delete the matching Slack message."""
    fake = FakeSlackWebClient()
    client = Team12SlackClient(token="xoxb-test", web_client=fake)

    client.delete_message("C123:1770000000.000001")

    assert fake.calls == [("chat_delete", {"channel": "C123", "ts": "1770000000.000001"})]


def test_delete_message_raises_when_slack_fails() -> None:
    """Raise a shared MessageDeleteError when Slack rejects deletion."""
    fake = FakeSlackWebClient()
    fake.delete_response = {"ok": False, "error": "cant_delete_message"}
    client = Team12SlackClient(token="xoxb-test", web_client=fake)

    with pytest.raises(MessageDeleteError):
        client.delete_message("C123:1770000000.000001")


def test_decode_message_id_rejects_invalid_shape() -> None:
    """Reject malformed opaque Slack message IDs."""
    with pytest.raises(ValueError, match="Expected"):
        _decode_message_id("not-a-slack-id")


def test_create_slack_chat_client_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create a Slack adapter from SLACK_BOT_TOKEN."""
    monkeypatch.setenv(SLACK_BOT_TOKEN_ENV, "xoxb-test")

    assert isinstance(create_slack_chat_client(), Team12SlackClient)
