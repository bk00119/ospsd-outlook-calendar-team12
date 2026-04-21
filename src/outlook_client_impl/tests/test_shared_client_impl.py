"""Tests for shared API implementation in outlook_client_impl."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from calendar_client_api.event import Event as LegacyEvent
from calendar_client_api.exceptions import CalendarNotFoundError
from ospsd_calendar_api.exceptions import CalendarOperationError, EventNotFoundError
from outlook_client_impl.shared_outlook_impl import OutlookSharedClient


class FakeLegacyEvent(LegacyEvent):
    """Minimal legacy event used for shared-client mapping tests."""

    def __init__(self, event_id: str, starts_at: datetime, ends_at: datetime) -> None:
        """Store fixture event values used by tests."""
        self._id = event_id
        self._starts_at = starts_at
        self._ends_at = ends_at

    @property
    def id(self) -> str:
        """Return event id."""
        return self._id

    @property
    def title(self) -> str:
        """Return title."""
        return "Title"

    @property
    def starts_at(self) -> datetime:
        """Return start datetime."""
        return self._starts_at

    @property
    def ends_at(self) -> datetime:
        """Return end datetime."""
        return self._ends_at

    @property
    def location(self) -> str | None:
        """Return location."""
        return "Room"

    @property
    def description(self) -> str | None:
        """Return description."""
        return "Desc"


def test_list_events_maps_to_shared_event_model() -> None:
    """Shared client should return ospsd Event models."""
    start = datetime(2026, 4, 11, 9, 0, tzinfo=UTC)
    end = datetime(2026, 4, 11, 10, 0, tzinfo=UTC)
    adjusted_end = end - timedelta(microseconds=1)
    legacy = MagicMock()
    legacy.list_events.return_value = [FakeLegacyEvent("evt-1", start, adjusted_end)]
    client = OutlookSharedClient(legacy_client=legacy)

    events = client.list_events(start=start, end=end)

    assert events[0].id == "evt-1"
    assert events[0].start_time == start
    assert events[0].end_time == adjusted_end
    legacy.list_events.assert_called_once_with(start=start, end=adjusted_end, types=None)


def test_update_event_maps_shared_kwargs_to_legacy_patch() -> None:
    """Shared kwargs should be converted into legacy EventPatch fields."""
    start = datetime(2026, 4, 11, 11, 0, tzinfo=UTC)
    end = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    legacy = MagicMock()
    legacy.update_event.return_value = FakeLegacyEvent("evt-2", start, end)
    client = OutlookSharedClient(legacy_client=legacy)

    updated = client.update_event("evt-2", title="Updated", start_time=start, end_time=end)

    assert updated.id == "evt-2"
    call_kwargs = legacy.update_event.call_args.kwargs
    payload = call_kwargs["payload"]
    assert payload.title == "Updated"
    assert payload.starts_at == start
    assert payload.ends_at == end


def test_not_found_maps_to_shared_not_found() -> None:
    """Legacy CalendarNotFoundError should map to shared EventNotFoundError."""
    legacy = MagicMock()
    legacy.get_event.side_effect = CalendarNotFoundError("missing")
    client = OutlookSharedClient(legacy_client=legacy)

    with pytest.raises(EventNotFoundError):
        client.get_event("missing-id")


def test_other_failures_map_to_shared_operation_error() -> None:
    """Non-not-found failures should map to CalendarOperationError."""
    legacy = MagicMock()
    legacy.delete_event.side_effect = RuntimeError("network down")
    client = OutlookSharedClient(legacy_client=legacy)

    with pytest.raises(CalendarOperationError):
        client.delete_event("evt-9")
