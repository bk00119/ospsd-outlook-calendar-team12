"""Unit tests for OutlookClient.list_events."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from outlook_client_impl.outlook_impl import OutlookClient

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

UTC = datetime.timezone.utc


def _make_item(
    event_id: str,
    subject: str = "Test Event",
    start: str = "2026-03-01T10:00:00+00:00",
    end: str = "2026-03-01T11:00:00+00:00",
    event_type: str = "singleInstance",
) -> dict[str, object]:
    """Return a minimal Graph API event payload dict."""
    return {
        "id": event_id,
        "subject": subject,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "type": event_type,
    }


class AsyncEventsBuilderStub:
    """Graph events-builder stub with async get()."""

    def __init__(self, items: list[object]) -> None:
        """Store the items to return from get()."""
        self._items = items

    async def get(self) -> object:
        """Return a stubbed collection response."""
        return SimpleNamespace(value=self._items)


class SyncEventsBuilderStub:
    """Graph events-builder stub with sync get()."""

    def __init__(self, items: list[object]) -> None:
        """Store the items to return from get()."""
        self._items = items

    def get(self) -> object:
        """Return a stubbed collection response."""
        return SimpleNamespace(value=self._items)


class NoGetEventsBuilderStub:
    """Graph events-builder stub without get()."""


@dataclass
class MeStub:
    """Graph me-builder stub."""

    events: object


@dataclass
class ServiceStub:
    """Graph service stub."""

    me: MeStub


def _client(items: list[object], *, sync: bool = False) -> OutlookClient:
    """Return an OutlookClient backed by a stub service."""
    builder = SyncEventsBuilderStub(items) if sync else AsyncEventsBuilderStub(items)
    stub = ServiceStub(me=MeStub(events=builder))
    return OutlookClient(service=cast("GraphServiceClient", stub))


# ---------------------------------------------------------------------------
# Basic listing
# ---------------------------------------------------------------------------


def test_list_events_returns_empty_list() -> None:
    """Returns an empty list when the provider returns no events."""
    assert _client([]).list_events() == []


def test_list_events_returns_all_events_unfiltered() -> None:
    """Returns all events when no filters are supplied."""
    items = [_make_item("e1", "Meeting"), _make_item("e2", "Lunch")]
    results = _client(items).list_events()

    assert len(results) == 2
    assert results[0].id == "e1"
    assert results[1].id == "e2"


def test_list_events_hydrates_event_title() -> None:
    """Returned events expose the title from the provider payload."""
    results = _client([_make_item("e1", "Architecture Review")]).list_events()

    assert results[0].title == "Architecture Review"


def test_list_events_works_with_sync_get() -> None:
    """Supports services whose get() is synchronous."""
    items = [_make_item("e1")]
    results = _client(items, sync=True).list_events()

    assert len(results) == 1
    assert results[0].id == "e1"


# ---------------------------------------------------------------------------
# Filter: start
# ---------------------------------------------------------------------------


def test_list_events_filter_start_excludes_earlier_events() -> None:
    """Events starting before `start` are excluded."""
    items = [
        _make_item("early", start="2026-03-01T08:00:00+00:00"),
        _make_item("late", start="2026-03-01T14:00:00+00:00"),
    ]
    cutoff = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    results = _client(items).list_events(start=cutoff)

    assert len(results) == 1
    assert results[0].id == "late"


def test_list_events_filter_start_includes_event_at_boundary() -> None:
    """An event starting exactly at `start` is included."""
    items = [_make_item("e1", start="2026-03-01T12:00:00+00:00")]
    cutoff = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    results = _client(items).list_events(start=cutoff)

    assert len(results) == 1


# ---------------------------------------------------------------------------
# Filter: end
# ---------------------------------------------------------------------------


def test_list_events_filter_end_excludes_later_events() -> None:
    """Events ending after `end` are excluded."""
    items = [
        _make_item("early", end="2026-03-01T10:00:00+00:00"),
        _make_item("late", end="2026-03-01T18:00:00+00:00"),
    ]
    cutoff = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    results = _client(items).list_events(end=cutoff)

    assert len(results) == 1
    assert results[0].id == "early"


def test_list_events_filter_end_includes_event_at_boundary() -> None:
    """An event ending exactly at `end` is included."""
    items = [_make_item("e1", end="2026-03-01T12:00:00+00:00")]
    cutoff = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    results = _client(items).list_events(end=cutoff)

    assert len(results) == 1


# ---------------------------------------------------------------------------
# Filter: types
# ---------------------------------------------------------------------------


def test_list_events_filter_types_single() -> None:
    """Only events matching the specified type are returned."""
    items = [
        _make_item("e1", event_type="singleInstance"),
        _make_item("e2", event_type="occurrence"),
        _make_item("e3", event_type="seriesMaster"),
    ]
    results = _client(items).list_events(types=["singleInstance"])

    assert len(results) == 1
    assert results[0].id == "e1"


def test_list_events_filter_types_multiple() -> None:
    """Events matching any of the specified types are returned."""
    items = [
        _make_item("e1", event_type="singleInstance"),
        _make_item("e2", event_type="occurrence"),
        _make_item("e3", event_type="seriesMaster"),
    ]
    results = _client(items).list_events(types=["singleInstance", "occurrence"])

    assert len(results) == 2
    assert {r.id for r in results} == {"e1", "e2"}


def test_list_events_filter_types_no_match_returns_empty() -> None:
    """Returns empty list when no events match the type filter."""
    items = [_make_item("e1", event_type="singleInstance")]
    results = _client(items).list_events(types=["seriesMaster"])

    assert results == []


# ---------------------------------------------------------------------------
# Combined filters
# ---------------------------------------------------------------------------


def test_list_events_combined_start_and_types() -> None:
    """start and types filters are applied together."""
    items = [
        _make_item("e1", start="2026-03-01T08:00:00+00:00", event_type="singleInstance"),
        _make_item("e2", start="2026-03-01T14:00:00+00:00", event_type="singleInstance"),
        _make_item("e3", start="2026-03-01T14:00:00+00:00", event_type="occurrence"),
    ]
    cutoff = datetime.datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    results = _client(items).list_events(start=cutoff, types=["singleInstance"])

    assert len(results) == 1
    assert results[0].id == "e2"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_list_events_raises_when_service_missing() -> None:
    """Raises RuntimeError when service is not configured."""
    client = object.__new__(OutlookClient)

    with pytest.raises(RuntimeError, match="not configured"):
        client.list_events()


def test_list_events_raises_when_service_has_no_me() -> None:
    """Raises NotImplementedError when service lacks me.events."""
    client = OutlookClient(service=cast("GraphServiceClient", object()))

    with pytest.raises(NotImplementedError, match="does not support event listing"):
        client.list_events()


def test_list_events_raises_when_events_builder_has_no_get() -> None:
    """Raises NotImplementedError when events builder lacks get()."""
    stub = ServiceStub(me=MeStub(events=NoGetEventsBuilderStub()))
    client = OutlookClient(service=cast("GraphServiceClient", stub))

    with pytest.raises(NotImplementedError, match="does not expose get"):
        client.list_events()


def test_list_events_raises_if_called_with_running_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raises RuntimeError with a clear message when an event loop is already active."""
    client = _client([_make_item("e1")])

    class _RunningLoop:
        def is_running(self) -> bool:
            return True

    def _fake_event_loop() -> _RunningLoop:
        return _RunningLoop()

    monkeypatch.setattr(
        "outlook_client_impl.outlook_impl.asyncio.get_event_loop",
        _fake_event_loop,
    )

    with pytest.raises(RuntimeError, match="cannot run inside an existing asyncio loop"):
        client.list_events()
