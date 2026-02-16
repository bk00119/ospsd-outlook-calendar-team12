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

    # TODO: fix the properties and methods as needed

    @property
    def title(self) -> str:
        """Get the event title."""
        val = self._parsed.get("subject", "No Subject")
        return str(val)

    @property
    def starts_at(self) -> datetime.datetime:
        """Get the event start time as a datetime object."""
        dt_str = self._parsed.get("start", {}).get("dateTime")
        if not dt_str:
            return datetime.datetime.min.replace(tzinfo=datetime.UTC)
        return datetime.datetime.fromisoformat(dt_str)

    @property
    def ends_at(self) -> datetime.datetime:
        """Get the event end time as a datetime object."""
        dt_str = self._parsed.get("end", {}).get("dateTime")
        if not dt_str:
            return datetime.datetime.min.replace(tzinfo=datetime.UTC)
        return datetime.datetime.fromisoformat(dt_str)

    @property
    def location(self) -> str:
        """Get the event location."""
        loc = self._parsed.get("location", {})
        val = loc.get("displayName", "")
        return str(val)

    @property
    def description(self) -> str:
        """Get the event description."""
        body = self._parsed.get("body", {})
        return str(body.get("content", self._parsed.get("bodyPreview", "")))

    @property
    def calendar_id(self) -> str:
        """Get the calendar ID associated with this event."""
        return str(self._parsed.get("calendarId", "Unknown Calendar"))


def get_event_impl(event_id: str, raw_data: str) -> event.Event:
    """Return an instance of the concrete OutlookCalendarEvent implementation."""
    return OutlookCalendarEvent(event_id=event_id, raw_data=raw_data)


def register() -> None:
    """Register the Outlook Calendar event implementation with the event abstraction."""
    event.get_event = get_event_impl
    calendar_client_api.get_event = get_event_impl
