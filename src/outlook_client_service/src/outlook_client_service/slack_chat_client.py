"""Team 12 Slack implementation of the shared ChatClient API."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from chat_client_api.client import (
    Channel,
    ChannelNotFoundError,
    ChatClient,
    Message,
    MessageDeleteError,
    MessageNotFoundError,
    register_client,
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN_ENV = "SLACK_BOT_TOKEN"  # noqa: S105
_MESSAGE_ID_SEPARATOR = ":"


class _SlackWebClient(Protocol):
    """Subset of Slack SDK WebClient used by this adapter."""

    def chat_postMessage(self, *, channel: str, text: str) -> object:  # noqa: N802
        """Post a Slack message."""

    def conversations_list(self, **kwargs: object) -> object:
        """List Slack conversations."""

    def conversations_info(self, *, channel: str) -> object:
        """Fetch one Slack conversation."""

    def conversations_history(self, **kwargs: object) -> object:
        """Fetch Slack conversation history."""

    def chat_delete(self, *, channel: str, ts: str) -> object:
        """Delete a Slack message."""


def _encode_message_id(channel_id: str, timestamp: str) -> str:
    """Encode Slack channel and timestamp into the shared opaque message ID."""
    return f"{channel_id}{_MESSAGE_ID_SEPARATOR}{timestamp}"


def _decode_message_id(message_id: str) -> tuple[str, str]:
    """Decode a shared opaque message ID into Slack channel and timestamp."""
    channel_id, separator, timestamp = message_id.partition(_MESSAGE_ID_SEPARATOR)
    if not separator or not channel_id or not timestamp:
        msg = f"Invalid Slack message_id: {message_id!r}. Expected 'channel_id:timestamp'."
        raise ValueError(msg)
    return channel_id, timestamp


def _datetime_from_slack_ts(timestamp: object) -> datetime:
    """Convert Slack's timestamp string into a timezone-aware datetime."""
    try:
        return datetime.fromtimestamp(float(str(timestamp)), tz=UTC)
    except ValueError:
        return datetime.fromtimestamp(0, tz=UTC)


def _require_ok(response: dict[str, Any], action: str) -> None:
    """Raise when Slack reports an unsuccessful API response."""
    if response.get("ok", False):
        return
    error = str(response.get("error", "unknown_error"))
    msg = f"Slack API failed during {action}: {error}"
    raise ValueError(msg)


def _as_dict(response: object) -> dict[str, Any]:
    """Convert a Slack SDK response into a plain dictionary."""
    if isinstance(response, dict):
        return response
    data = getattr(response, "data", None)
    if isinstance(data, dict):
        return cast("dict[str, Any]", data)
    msg = "Slack response could not be converted to a dictionary."
    raise TypeError(msg)


def _message_from_payload(channel_id: str, payload: dict[str, Any]) -> Message:
    """Map a Slack message payload into the shared Message model."""
    timestamp = str(payload.get("ts", ""))
    return Message(
        message_id=_encode_message_id(channel_id, timestamp),
        channel=channel_id,
        text=str(payload.get("text", "")),
        sender=str(payload.get("user") or payload.get("bot_id") or "unknown"),
        timestamp=_datetime_from_slack_ts(timestamp),
    )


def _channel_from_payload(payload: dict[str, Any]) -> Channel:
    """Map a Slack conversation payload into the shared Channel model."""
    return Channel(
        channel_id=str(payload.get("id", "")),
        name=str(payload.get("name", "")),
        is_private=bool(payload.get("is_private")) if "is_private" in payload else None,
        channel_type=str(payload.get("is_channel", "")) if "is_channel" in payload else None,
    )


class Team12SlackClient(ChatClient):
    """Slack-backed implementation of the shared ChatClient API."""

    def __init__(self, token: str, web_client: object | None = None) -> None:
        """Initialize the adapter with a Slack bot token or injected WebClient."""
        if not token:
            msg = f"{SLACK_BOT_TOKEN_ENV} environment variable must be set."
            raise ValueError(msg)
        self._client = cast("_SlackWebClient", web_client or WebClient(token=token))

    def send_message(self, channel_id: str, text: str) -> Message:
        """Send a message to a Slack channel."""
        try:
            response = _as_dict(self._client.chat_postMessage(channel=channel_id, text=text))
        except SlackApiError as exc:
            msg = f"Failed to send Slack message to {channel_id}: {exc.response.get('error', 'unknown')}"
            raise ValueError(msg) from exc
        _require_ok(response, "chat_postMessage")
        timestamp = str(response.get("ts", ""))
        resolved_channel = str(response.get("channel", channel_id))
        message_payload = response.get("message")
        text_value = (
            str(message_payload.get("text", text))
            if isinstance(message_payload, dict)
            else text
        )
        return Message(
            message_id=_encode_message_id(resolved_channel, timestamp),
            channel=resolved_channel,
            text=text_value,
            sender=str(response.get("bot_id") or "bot"),
            timestamp=_datetime_from_slack_ts(timestamp),
        )

    def get_channels(self) -> list[Channel]:
        """List Slack conversations visible to the bot."""
        channels: list[Channel] = []
        cursor: str | None = None
        while True:
            kwargs: dict[str, Any] = {"exclude_archived": True, "limit": 200}
            if cursor:
                kwargs["cursor"] = cursor
            response = _as_dict(self._client.conversations_list(**kwargs))
            _require_ok(response, "conversations_list")
            channels.extend(
                _channel_from_payload(channel)
                for channel in response.get("channels", [])
                if isinstance(channel, dict)
            )
            metadata = response.get("response_metadata")
            cursor = (
                str(metadata.get("next_cursor", ""))
                if isinstance(metadata, dict)
                else ""
            )
            if not cursor:
                return channels

    def get_channel(self, channel_id: str) -> Channel:
        """Get one Slack conversation by channel ID."""
        try:
            response = _as_dict(self._client.conversations_info(channel=channel_id))
        except SlackApiError as exc:
            msg = f"Slack channel not found: {channel_id}"
            raise ChannelNotFoundError(msg) from exc
        _require_ok(response, "conversations_info")
        channel = response.get("channel")
        if not isinstance(channel, dict):
            msg = f"Slack channel not found: {channel_id}"
            raise ChannelNotFoundError(msg)
        return _channel_from_payload(channel)

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        """Get recent Slack messages from a channel."""
        kwargs: dict[str, Any] = {"channel": channel_id, "limit": limit}
        if cursor:
            kwargs["cursor"] = cursor
        response = _as_dict(self._client.conversations_history(**kwargs))
        _require_ok(response, "conversations_history")
        return [
            _message_from_payload(channel_id, message)
            for message in response.get("messages", [])
            if isinstance(message, dict)
        ]

    def get_message(self, message_id: str) -> Message:
        """Get one Slack message by opaque message ID."""
        channel_id, timestamp = _decode_message_id(message_id)
        try:
            response = _as_dict(self._client.conversations_history(
                channel=channel_id,
                latest=timestamp,
                oldest=timestamp,
                inclusive=True,
                limit=1,
            ))
        except SlackApiError as exc:
            msg = f"Slack message not found: {message_id}"
            raise MessageNotFoundError(msg) from exc
        _require_ok(response, "conversations_history")
        messages: list[Any] = response.get("messages", [])
        if not messages or not isinstance(messages[0], dict):
            msg = f"Slack message not found: {message_id}"
            raise MessageNotFoundError(msg)
        return _message_from_payload(channel_id, messages[0])

    def delete_message(self, message_id: str) -> None:
        """Delete one Slack message by opaque message ID."""
        channel_id, timestamp = _decode_message_id(message_id)
        try:
            response = _as_dict(self._client.chat_delete(channel=channel_id, ts=timestamp))
            _require_ok(response, "chat_delete")
        except SlackApiError as exc:
            msg = f"Failed to delete Slack message: {message_id}"
            raise MessageDeleteError(msg) from exc
        except ValueError as exc:
            msg = f"Failed to delete Slack message: {message_id}"
            raise MessageDeleteError(msg) from exc


def create_slack_chat_client() -> Team12SlackClient:
    """Create the Team 12 Slack adapter from environment variables."""
    token = os.getenv(SLACK_BOT_TOKEN_ENV, "")
    return Team12SlackClient(token=token)


register_client(create_slack_chat_client)
