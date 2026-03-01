"""Unit tests for OutlookClient.create_event."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from outlook_client_impl.outlook_impl import OutlookClient


class AsyncEventsBuilderStub:
    """Graph events request-builder stub with async post()."""

    def __init__(self) -> None:
        self.last_payload: object | None = None

    async def post(self, payload: object) -> object:
        self.last_payload = payload
        return {
            "id": "created-123",
            "subject": "Team Sync",
            "start": {"dateTime": "2026-03-02T15:00:00", "timeZone": "UTC"},
            "end": {"dateTime": "2026-03-02T16:00:00", "timeZone": "UTC"},
            "location": {"displayName": "Room B"},
            "body": {"content": "Status update"},
        }


class SyncEventsBuilderStub:
    """Graph events request-builder stub with sync post()."""

    def post(self, payload: object) -> object:
        _ = payload
        return {"id": "created-sync-1", "subject": "Sync Builder Event"}


def _client_with_events_builder(events_builder: object) -> OutlookClient:
    service = SimpleNamespace(me=SimpleNamespace(events=events_builder))
    return OutlookClient(service=service)


def test_create_event_builds_payload_and_returns_hydrated_event() -> None:
    events_builder = AsyncEventsBuilderStub()
    client = _client_with_events_builder(events_builder)

    result = client.create_event(
        title="  Team Sync  ",
        starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
        ends_at=datetime(2026, 3, 2, 16, 0, tzinfo=UTC),
        location=" Room B ",
        description=" Status update ",
    )

    assert events_builder.last_payload == {
        "subject": "Team Sync",
        "start": {"dateTime": "2026-03-02T15:00:00", "timeZone": "UTC"},
        "end": {"dateTime": "2026-03-02T16:00:00", "timeZone": "UTC"},
        "location": {"displayName": "Room B"},
        "body": {"contentType": "text", "content": "Status update"},
    }
    assert result.id == "created-123"
    assert result.title == "Team Sync"
    assert result.location == "Room B"


def test_create_event_supports_sync_post_result() -> None:
    client = _client_with_events_builder(SyncEventsBuilderStub())

    result = client.create_event(
        title="Sync Builder Event",
        starts_at=datetime(2026, 3, 2, 18, 0, tzinfo=UTC),
        ends_at=datetime(2026, 3, 2, 19, 0, tzinfo=UTC),
    )

    assert result.id == "created-sync-1"
    assert result.title == "Sync Builder Event"


@pytest.mark.parametrize("title", ["", "   "])
def test_create_event_rejects_empty_title(title: str) -> None:
    client = _client_with_events_builder(AsyncEventsBuilderStub())

    with pytest.raises(ValueError, match="title must be a non-empty string"):
        client.create_event(
            title=title,
            starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
            ends_at=datetime(2026, 3, 2, 16, 0, tzinfo=UTC),
        )


def test_create_event_rejects_invalid_time_range() -> None:
    client = _client_with_events_builder(AsyncEventsBuilderStub())

    with pytest.raises(ValueError, match="must be after"):
        client.create_event(
            title="Team Sync",
            starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
            ends_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
        )


def test_create_event_raises_when_service_missing() -> None:
    client = object.__new__(OutlookClient)

    with pytest.raises(RuntimeError, match="not configured"):
        client.create_event(
            title="Team Sync",
            starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
            ends_at=datetime(2026, 3, 2, 16, 0, tzinfo=UTC),
        )


def test_create_event_raises_for_unsupported_service_shape() -> None:
    client = OutlookClient(service=object())

    with pytest.raises(NotImplementedError, match="does not support event creation"):
        client.create_event(
            title="Team Sync",
            starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
            ends_at=datetime(2026, 3, 2, 16, 0, tzinfo=UTC),
        )


def test_create_event_raises_when_create_returns_none() -> None:
    class _NoneEventsBuilder:
        async def post(self, payload: object) -> object:
            _ = payload
            return None

    client = _client_with_events_builder(_NoneEventsBuilder())

    with pytest.raises(RuntimeError, match="returned no payload"):
        client.create_event(
            title="Team Sync",
            starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
            ends_at=datetime(2026, 3, 2, 16, 0, tzinfo=UTC),
        )


def test_create_event_raises_when_payload_missing_id() -> None:
    class _NoIdEventsBuilder:
        async def post(self, payload: object) -> object:
            _ = payload
            return {"subject": "Missing Id"}

    client = _client_with_events_builder(_NoIdEventsBuilder())

    with pytest.raises(RuntimeError, match="valid id"):
        client.create_event(
            title="Team Sync",
            starts_at=datetime(2026, 3, 2, 15, 0, tzinfo=UTC),
            ends_at=datetime(2026, 3, 2, 16, 0, tzinfo=UTC),
        )
