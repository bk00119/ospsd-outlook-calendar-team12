"""Unit tests for Slack poller."""

import time as time_module
from dataclasses import dataclass

import pytest
from chat_client_api.client import Message

from outlook_client_service import slack_poller

NEW_MESSAGE_TIMESTAMP = 101.0

class StopPollingError(Exception):
    """Stop the infinite polling loop during tests."""


@dataclass
class FakeChatClient:
    """Fake chat client for polling tests."""

    messages: list[Message]
    sent_messages: list[tuple[str, str]]

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        """Return fake Slack messages."""
        return self.messages

    def send_message(self, channel_id: str, text: str) -> Message:
        """Record fake Slack replies."""
        self.sent_messages.append((channel_id, text))
        return Message(
            message_id="sent-message-id",
            channel=channel_id,
            text=text,
            sender="BOT_USER",
            timestamp="9999999999.0",
        )


class FakeIntelligentAppService:
    """Fake intelligent app service for polling tests."""

    def __init__(self) -> None:
        """Initialize recorded calls."""
        self.calls: list[tuple[str, str]] = []

    def process_chat(self, message: str, user_timezone: str = "UTC") -> str:
        """Record processed messages and return a fake reply."""
        self.calls.append((message, user_timezone))
        return f"reply: {message}"


def _message(
    message_id: str,
    text: str,
    sender: str = "USER_1",
    timestamp: str = "9999999999.0",
) -> Message:
    """Build a fake chat message."""
    return Message(
        message_id=message_id,
        channel="C_TEST",
        text=text,
        sender=sender,
        timestamp=timestamp,
    )


def test_message_guard_skips_messages_without_bot_mention() -> None:
    """Skip messages that do not mention the bot."""
    store = slack_poller.ProcessedMessageStore(max_size=100)
    guard = slack_poller.SlackMessageGuard("BOT_USER", store)
    guard.last_seen_timestamp = 100.0

    should_process, message_timestamp = guard.should_process(
        message_id="m1",
        sender="USER_1",
        text="hello",
        timestamp="101.0",
    )

    assert should_process is False
    assert message_timestamp == NEW_MESSAGE_TIMESTAMP
    assert store.contains("m1") is True


def test_message_guard_skips_bot_messages() -> None:
    """Skip messages sent by the bot itself."""
    store = slack_poller.ProcessedMessageStore(max_size=100)
    guard = slack_poller.SlackMessageGuard("BOT_USER", store)
    guard.last_seen_timestamp = 100.0

    should_process, message_timestamp = guard.should_process(
        message_id="m1",
        sender="BOT_USER",
        text="<@BOT_USER> hello",
        timestamp="101.0",
    )

    assert should_process is False
    assert message_timestamp == NEW_MESSAGE_TIMESTAMP
    assert store.contains("m1") is True


def test_message_guard_processes_new_bot_mentions() -> None:
    """Process new messages that mention the bot."""
    store = slack_poller.ProcessedMessageStore(max_size=100)
    guard = slack_poller.SlackMessageGuard("BOT_USER", store)
    guard.last_seen_timestamp = 100.0

    should_process, message_timestamp = guard.should_process(
        message_id="m1",
        sender="USER_1",
        text="<@BOT_USER> list my events today",
        timestamp="101.0",
    )

    assert should_process is True
    assert message_timestamp == NEW_MESSAGE_TIMESTAMP


def test_processed_message_store_evicts_oldest_ids() -> None:
    """Evict oldest processed IDs after reaching max size."""
    store = slack_poller.ProcessedMessageStore(max_size=2)

    store.mark("m1")
    store.mark("m2")
    store.mark("m3")

    assert store.contains("m1") is False
    assert store.contains("m2") is True
    assert store.contains("m3") is True


def test_run_slack_poller_routes_mention_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route one mention message to the intelligent app service and reply in Slack."""
    fake_chat = FakeChatClient(
        messages=[_message("m1", "<@BOT_USER> list my events today")],
        sent_messages=[],
    )
    fake_service = FakeIntelligentAppService()

    monkeypatch.setenv(slack_poller.BOT_USER_ID_ENV, "BOT_USER")
    monkeypatch.setenv(slack_poller.CHANNEL_ID_ENV, "C_TEST")
    monkeypatch.setenv(slack_poller.USER_TIMEZONE_ENV, "America/New_York")
    monkeypatch.setattr(slack_poller, "get_client", lambda: fake_chat)
    monkeypatch.setattr(slack_poller, "get_intelligent_app", lambda: fake_service)
    monkeypatch.setattr(
        time_module,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(StopPollingError),
    )

    with pytest.raises(StopPollingError):
        slack_poller.run_slack_poller()

    assert fake_service.calls == [("list my events today", "America/New_York")]
    assert fake_chat.sent_messages == [("C_TEST", "reply: list my events today")]


def test_run_slack_poller_ignores_non_mentions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not call the service for messages that do not mention the bot."""
    fake_chat = FakeChatClient(
        messages=[_message("m1", "list my events today")],
        sent_messages=[],
    )
    fake_service = FakeIntelligentAppService()

    monkeypatch.setenv(slack_poller.BOT_USER_ID_ENV, "BOT_USER")
    monkeypatch.setenv(slack_poller.CHANNEL_ID_ENV, "C_TEST")
    monkeypatch.setattr(slack_poller, "get_client", lambda: fake_chat)
    monkeypatch.setattr(slack_poller, "get_intelligent_app", lambda: fake_service)
    monkeypatch.setattr(
        time_module,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(StopPollingError),
    )

    with pytest.raises(StopPollingError):
        slack_poller.run_slack_poller()

    assert fake_service.calls == []
    assert fake_chat.sent_messages == []
