"""Unit tests for the Google Calendar provider."""

from datetime import UTC, datetime

import pytest
from outlook_client_service.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarEvent,
)


class TestGoogleCalendarEvent:
    """Test the concrete Google event implementation."""

    def test_event_properties_return_expected_values(self) -> None:
        """Expose the shared Event properties correctly."""
        starts_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        ends_at = datetime(2026, 5, 1, 11, 0, tzinfo=UTC)

        event = GoogleCalendarEvent(
            event_id="abc123",
            title="Demo Meeting",
            starts_at=starts_at,
            ends_at=ends_at,
            location="NYU",
            description="Provider swap demo",
        )

        assert event.id == "abc123"
        assert event.title == "Demo Meeting"
        assert event.starts_at == starts_at
        assert event.ends_at == ends_at
        assert event.location == "NYU"
        assert event.description == "Provider swap demo"


class TestGoogleCalendarClient:
    """Test provider-specific helper methods."""

    def test_validate_datetime_raises_for_naive_datetime(self) -> None:
        """Reject naive datetimes before provider calls."""
        naive_datetime = datetime.fromisoformat("2026-05-01T10:00:00")

        with pytest.raises(ValueError, match="timezone-aware"):
            GoogleCalendarClient._validate_datetime(naive_datetime)

    def test_build_event_body_returns_google_payload(self) -> None:
        """Convert shared create fields into Google request payload."""
        starts_at = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        ends_at = datetime(2026, 5, 1, 11, 0, tzinfo=UTC)

        payload = GoogleCalendarClient._build_event_body(
            title="Demo Meeting",
            starts_at=starts_at,
            ends_at=ends_at,
            location="NYU",
            description="Provider swap demo",
        )

        assert payload["summary"] == "Demo Meeting"
        assert payload["location"] == "NYU"
        assert payload["description"] == "Provider swap demo"

    def test_to_event_maps_google_payload_to_shared_event(self) -> None:
        """Convert Google API payload into a shared event object."""
        event = GoogleCalendarClient._to_event(
            {
                "id": "google-123",
                "summary": "Demo Meeting",
                "start": {"dateTime": "2026-05-01T10:00:00+00:00"},
                "end": {"dateTime": "2026-05-01T11:00:00+00:00"},
                "location": "NYU",
                "description": "Provider swap demo",
            },
        )

        assert event.id == "google-123"
        assert event.title == "Demo Meeting"
        assert event.location == "NYU"
