"""Unit tests for event routes."""

from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import create_autospec

import pytest
from calendar_client_api.event import EventPatch
from fastapi import HTTPException
from outlook_client_impl.event_impl import OutlookCalendarEvent
from outlook_client_impl.outlook_impl import OutlookClient
from outlook_client_service.routers.events import create_event, delete_event, update_event
from outlook_client_service.schemas.event import EventCreateRequest, EventResponse, EventUpdateRequest


class TestCreateEvent:
    """Group tests for creating an event."""

    def setup_method(self) -> None:
        """Create shared request data and client doubles for each test."""
        self.event_id = "event-123"
        self.starts_at = datetime(2026, 3, 20, 9, 0, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 20, 10, 0, 0, tzinfo=UTC)
        self.request = EventCreateRequest(
            title="Created title",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room 101",
            description="Created description.",
        )
        self.client = create_autospec(OutlookClient, instance=True)

    def _build_created_event(self) -> OutlookCalendarEvent:
        """Build a concrete OutlookCalendarEvent returned by the client."""
        raw = {
            "subject": "Created title",
            "start": {"dateTime": self.starts_at.isoformat()},
            "end": {"dateTime": self.ends_at.isoformat()},
            "location": {"displayName": "Room 101"},
            "body": {"content": "Created description."},
        }
        import json

        return OutlookCalendarEvent(self.event_id, json.dumps(raw))

    def test_call_client_create(self) -> None:
        """Call the client with the request payload."""
        self.client.create_event.return_value = self._build_created_event()

        create_event(self.request, self.client)

        self.client.create_event.assert_called_once_with(
            title="Created title",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room 101",
            description="Created description.",
        )

    def test_return_mapped_event_response(self) -> None:
        """Return a mapped EventResponse after a successful create."""
        self.client.create_event.return_value = self._build_created_event()

        response = create_event(self.request, self.client)

        assert response == EventResponse(
            id=self.event_id,
            title="Created title",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room 101",
            description="Created description.",
        )

    def test_wrap_client_exception_as_http_502(self) -> None:
        """Wrap a client failure in an HTTP 502 exception."""
        self.client.create_event.side_effect = RuntimeError("boom")

        with pytest.raises(HTTPException) as exc_info:
            create_event(self.request, self.client)

        assert exc_info.value.status_code == HTTPStatus.BAD_GATEWAY
        assert exc_info.value.detail == "Failed to create event: boom"


class TestUpdateEvent:
    """Group tests for partially updating an event."""

    def setup_method(self) -> None:
        """Create shared request data and client doubles for each test."""
        self.event_id = "event-123"
        self.starts_at = datetime(2026, 3, 20, 9, 0, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 20, 10, 0, 0, tzinfo=UTC)
        self.request = EventUpdateRequest(
            title="Updated title",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room 202",
            description="Updated description.",
        )
        self.client = create_autospec(OutlookClient, instance=True)

    def _build_updated_event(self) -> OutlookCalendarEvent:
        """Build a concrete OutlookCalendarEvent returned by the client."""
        raw = {
            "subject": "Updated title",
            "start": {"dateTime": self.starts_at.isoformat()},
            "end": {"dateTime": self.ends_at.isoformat()},
            "location": {"displayName": "Room 202"},
            "body": {"content": "Updated description."},
        }
        import json

        return OutlookCalendarEvent(self.event_id, json.dumps(raw))

    def test_build_patch_and_call_client(self) -> None:
        """Build an EventPatch and call the client once."""
        self.client.update_event.return_value = self._build_updated_event()

        update_event(self.event_id, self.request, self.client)

        self.client.update_event.assert_called_once()
        call_kwargs = self.client.update_event.call_args.kwargs
        assert call_kwargs["event_id"] == self.event_id
        assert isinstance(call_kwargs["payload"], EventPatch)
        assert call_kwargs["payload"] == EventPatch(
            title="Updated title",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room 202",
            description="Updated description.",
        )

    def test_return_mapped_event_response(self) -> None:
        """Return a mapped EventResponse after a successful update."""
        self.client.update_event.return_value = self._build_updated_event()

        response = update_event(self.event_id, self.request, self.client)

        assert response == EventResponse(
            id=self.event_id,
            title="Updated title",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room 202",
            description="Updated description.",
        )

    def test_wrap_client_exception_as_http_502(self) -> None:
        """Wrap a client failure in an HTTP 502 exception."""
        self.client.update_event.side_effect = RuntimeError("boom")

        with pytest.raises(HTTPException) as exc_info:
            update_event(self.event_id, self.request, self.client)

        assert exc_info.value.status_code == HTTPStatus.BAD_GATEWAY
        assert exc_info.value.detail == "Failed to update event: boom"


class TestDeleteEvent:
    """Group tests for deleting an event."""

    def setup_method(self) -> None:
        """Create shared client double for each test."""
        self.event_id = "event-123"
        self.client = create_autospec(OutlookClient, instance=True)

    def test_call_client_delete(self) -> None:
        """Call the client's delete_event method once."""
        delete_event(self.event_id, self.client)

        self.client.delete_event.assert_called_once_with(event_id=self.event_id)

    def test_wrap_client_exception_as_http_502(self) -> None:
        """Wrap a client failure in an HTTP 502 exception."""
        self.client.delete_event.side_effect = RuntimeError("Error")

        with pytest.raises(HTTPException) as exc_info:
            delete_event(self.event_id, self.client)

        assert exc_info.value.status_code == HTTPStatus.BAD_GATEWAY
        assert exc_info.value.detail == "Failed to delete event: Error"

    def test_return_none_on_success(self) -> None:
        """Return None for a successful deletion (HTTP 204)."""
        result = delete_event(self.event_id, self.client)
        assert result is None
