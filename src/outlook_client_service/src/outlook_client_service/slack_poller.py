"""Slack polling loop for mention-based calendar assistant."""

from __future__ import annotations

import logging
import os
import re
import time
from collections import deque
from threading import Thread

import slack_client_impl  # noqa: F401
from chat_client_api.client import get_client
from dotenv import load_dotenv
from intelligent_app_service.wiring import get_intelligent_app

from outlook_client_service.config import settings
from outlook_client_service.dependencies import get_calendar_client_for_slack_user
from outlook_client_service.routers.auth import SLACK_AUTH_QUERY_PARAM, create_slack_auth_token

POLL_INTERVAL_SECONDS = 3
DEFAULT_LIMIT = 20
MAX_PROCESSED_IDS = 1000

BOT_USER_ID_ENV = "SLACK_BOT_USER_ID"
CHANNEL_ID_ENV = "SLACK_TEST_CHANNEL_ID"
USER_TIMEZONE_ENV = "SLACK_USER_TIMEZONE"
DEFAULT_USER_TIMEZONE = "America/New_York"

logger = logging.getLogger(__name__)

_poller_thread: Thread | None = None

class ProcessedMessageStore:
    """Track processed Slack message IDs with bounded memory growth."""

    def __init__(self, max_size: int) -> None:
        """Initialize the processed message store."""
        self._max_size = max_size
        self._ids: set[str] = set()
        self._order: deque[str] = deque()

    def contains(self, message_id: str) -> bool:
        """Return True if the message ID was already processed."""
        return message_id in self._ids

    def mark(self, message_id: str) -> None:
        """Record a processed message ID."""
        self._ids.add(message_id)
        self._order.append(message_id)
        while len(self._order) > self._max_size:
            oldest_id = self._order.popleft()
            self._ids.discard(oldest_id)


class SlackMessageGuard:
    """Decide whether Slack messages should be processed."""

    def __init__(self, bot_user_id: str, processed_store: ProcessedMessageStore) -> None:
        """Initialize the guard with bot identity and processed-message storage."""
        self._bot_user_id = bot_user_id
        self._processed_store = processed_store
        self.last_seen_timestamp = time.time()

    def should_process(
        self,
        message_id: str,
        sender: str,
        text: str,
        timestamp: str,
    ) -> tuple[bool, float | None]:
        """Return whether a Slack message should be processed."""
        if self._processed_store.contains(message_id):
            return False, None

        message_timestamp = _parse_message_timestamp(timestamp)
        if message_timestamp is None:
            self._processed_store.mark(message_id)
            return False, None

        if message_timestamp <= self.last_seen_timestamp:
            return False, message_timestamp

        if _is_bot_message(sender, self._bot_user_id):
            logger.debug("Skipping bot message: %s", message_id)
            self._processed_store.mark(message_id)
            return False, message_timestamp

        if not _is_bot_mentioned(text, self._bot_user_id):
            logger.debug("Skipping message without bot mention: %s", message_id)
            self._processed_store.mark(message_id)
            return False, message_timestamp

        return True, message_timestamp

    def mark_seen(self, message_timestamp: float | None) -> None:
        """Update the latest observed Slack message timestamp."""
        if message_timestamp is not None:
            self.last_seen_timestamp = max(self.last_seen_timestamp, message_timestamp)


def _is_bot_message(sender: str, bot_user_id: str) -> bool:
    """Return True if the message is sent by the bot itself."""
    return sender == bot_user_id


def _is_bot_mentioned(text: str, bot_user_id: str) -> bool:
    """Return True if the bot is mentioned in the message text."""
    return f"<@{bot_user_id}>" in text


def _strip_bot_mention(text: str, bot_user_id: str) -> str:
    """Remove bot mention from text and return cleaned user message."""
    return text.replace(f"<@{bot_user_id}>", "").strip()


def _parse_message_timestamp(timestamp: str) -> float | None:
    """Parse a chat message timestamp into a comparable float."""
    try:
        return float(timestamp)
    except ValueError:
        logger.warning("Could not parse message timestamp: %s", timestamp)
        return None


def _format_slack_reply(text: str) -> str:
    """Convert common Markdown output into Slack-friendly mrkdwn."""
    formatted = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    formatted = re.sub(r"(?m)^\s*\*\s+", "• ", formatted)
    return re.sub(r"(?m)^\s*-\s+", "• ", formatted)


def _require_env(name: str, value: str | None) -> str:
    """Return an environment variable value or raise if missing."""
    if value:
        return value
    err_msg = f"{name} must be set"
    raise ValueError(err_msg)


def _build_auth_link(slack_user_id: str) -> str:
    """Build an authentication link for a Slack user."""
    slack_auth_token = create_slack_auth_token(slack_user_id)
    return f"{settings.azure_login_uri}?{SLACK_AUTH_QUERY_PARAM}={slack_auth_token}"


def _handle_message(
    sender: str,
    text: str,
    bot_user_id: str,
    user_timezone: str,
) -> str | None:
    """Process one Slack message and return a reply if needed."""
    user_text = _strip_bot_mention(text, bot_user_id)
    if not user_text:
        return None

    calendar_client = get_calendar_client_for_slack_user(sender)

    if calendar_client is None:
        auth_link = _build_auth_link(sender)
        return f"<@{sender}> Please connect your calendar first: {auth_link}"

    service = get_intelligent_app(calendar_client=calendar_client)

    logger.info("Processing Slack message from %s: %s", sender, user_text)
    try:
        return service.process_chat(
            message=user_text,
            user_timezone=user_timezone,
        )
    except Exception as exc:  # noqa: BLE001
        return f"Error processing request: {exc}"


def run_slack_poller() -> None:
    """Poll Slack and route mention requests to the app service."""
    load_dotenv()

    bot_user_id = _require_env(BOT_USER_ID_ENV, os.getenv(BOT_USER_ID_ENV))
    channel_id = _require_env(CHANNEL_ID_ENV, os.getenv(CHANNEL_ID_ENV))
    user_timezone = os.getenv(USER_TIMEZONE_ENV, DEFAULT_USER_TIMEZONE)

    chat_client = get_client()

    processed_store = ProcessedMessageStore(MAX_PROCESSED_IDS)
    message_guard = SlackMessageGuard(bot_user_id, processed_store)

    logger.info(
        "Starting Slack poller on channel %s with timezone %s...",
        channel_id,
        user_timezone,
    )

    while True:
        try:
            messages = chat_client.get_messages(
                channel_id=channel_id,
                limit=DEFAULT_LIMIT,
            )

            for msg in reversed(messages):
                should_process, message_timestamp = message_guard.should_process(
                    message_id=msg.message_id,
                    sender=msg.sender,
                    text=msg.text,
                    timestamp=msg.timestamp,
                )
                message_guard.mark_seen(message_timestamp)
                if not should_process:
                    continue

                response = _handle_message(
                    sender=msg.sender,
                    text=msg.text,
                    bot_user_id=bot_user_id,
                    user_timezone=user_timezone,
                )
                if response is None:
                    processed_store.mark(msg.message_id)
                    continue

                logger.info("Sending Slack reply for message %s", msg.message_id)
                sender_mention = f"<@{msg.sender}>"
                response = _format_slack_reply(response)
                final_reply = (
                    response
                    if response.startswith(sender_mention)
                    else f"{sender_mention} {response}"
                )
                chat_client.send_message(
                    channel_id=channel_id,
                    text=final_reply,
                )
                processed_store.mark(msg.message_id)

        except Exception:
            logger.exception("Slack polling loop error")

        time.sleep(POLL_INTERVAL_SECONDS)


def start_slack_poller_background() -> None:
    """Start the Slack poller in a daemon background thread."""
    global _poller_thread  # noqa: PLW0603
    if _poller_thread is not None and _poller_thread.is_alive():
        logger.info("Slack poller background thread is already running.")
        return

    _poller_thread = Thread(
        target=run_slack_poller,
        name="slack-poller",
        daemon=True,
    )
    _poller_thread.start()
    logger.info("Started Slack poller background thread.")
