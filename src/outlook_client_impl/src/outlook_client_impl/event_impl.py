"""Outlook Calendar Implementation colocated with the Outlook client."""

import datetime
import json
import logging

import calendar_client_api
from calendar_client_api import event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OutlookCalendarEvent(event.Event):
    """Concrete implementation of the Event abstraction for Outlook Calendar events."""

    def __init__(self, event_id: str, raw_data: str) -> None:
        """Decode the Outlook payload and hydrate event metadata."""
        self._id = event_id
        self._raw_data = raw_data

        try:
            # Decode the Outlook JSON payload
            data = json.loads(raw_data)
            self._parsed = data
        except (json.JSONDecodeError, TypeError):
            logger.exception("Failed to decode Outlook event data for %s", event_id)
            self._parsed = {}

    @property
    def id(self) -> str:
        """Get the unique event identifier."""
        return self._id

    def _parse_datetime(self, value: object) -> datetime.datetime:
        """Parse Graph datetime strings and normalize to timezone-aware values."""
        if not isinstance(value, str) or not value:
            return datetime.datetime.min.replace(tzinfo=datetime.UTC)

        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.datetime.min.replace(tzinfo=datetime.UTC)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=datetime.UTC)
        return parsed

    @property
    def title(self) -> str:
        """Get the event title."""
        val = self._parsed.get("subject", "No Subject")
        return str(val)

    @property
    def starts_at(self) -> datetime.datetime:
        """Get the event start time as a datetime object."""
        start_data = self._parsed.get("start", {})
        dt_value = start_data.get("dateTime") if isinstance(start_data, dict) else None
        return self._parse_datetime(dt_value)

    @property
    def ends_at(self) -> datetime.datetime:
        """Get the event end time as a datetime object."""
        end_data = self._parsed.get("end", {})
        dt_value = end_data.get("dateTime") if isinstance(end_data, dict) else None
        return self._parse_datetime(dt_value)

    @property
    def location(self) -> str | None:
        """Get the event location."""
        loc = self._parsed.get("location", {})
        val = loc.get("displayName") if isinstance(loc, dict) else None
        if val is None:
            return None
        clean = str(val).strip()
        return clean or None

    @property
    def description(self) -> str | None:
        """Get the event description."""
        body = self._parsed.get("body", {})
        content: object | None = None
        if isinstance(body, dict):
            content = body.get("content")
        if content is None:
            content = self._parsed.get("bodyPreview")
        if content is None:
            return None
        clean = str(content).strip()
        return clean or None


def get_event_impl(event_id: str, raw_data: str) -> event.Event:
    """Return an instance of the concrete OutlookCalendarEvent implementation."""
    return OutlookCalendarEvent(event_id=event_id, raw_data=raw_data)


def register() -> None:
    """Register the Outlook Calendar event implementation with the event abstraction."""
    event.get_event = get_event_impl
    calendar_client_api.get_event = get_event_impl
