"""Shared calendar API implementation backed by the existing Outlook client."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from calendar_client_api.exceptions import CalendarNotFoundError
from ospsd_calendar_api.client import CalendarClient as SharedCalendarClient
from ospsd_calendar_api.exceptions import (
    CalendarOperationError as SharedCalendarOperationError,
)
from ospsd_calendar_api.exceptions import (
    EventNotFoundError as SharedEventNotFoundError,
)
from ospsd_calendar_api.models import Event as SharedEvent

from calendar_client_api import event as legacy_event
from outlook_client_impl.outlook_impl import OutlookClient

if TYPE_CHECKING:
    from datetime import datetime

    from calendar_client_api.event import Event as LegacyEvent
    from msgraph.graph_service_client import GraphServiceClient


class OutlookSharedClient(SharedCalendarClient):
    """Shared-API implementation backed by the existing OutlookClient."""

    def __init__(
        self,
        *,
        service: GraphServiceClient | None = None,
        interactive: bool = False,
        legacy_client: OutlookClient | None = None,
    ) -> None:
        """Create a shared client backed by the legacy Outlook implementation."""
        self._legacy_client = legacy_client or OutlookClient(
            service=service,
            interactive=interactive,
        )

    @staticmethod
    def _to_shared_event(legacy_evt: LegacyEvent) -> SharedEvent:
        """Map legacy event objects to the shared Event model."""
        return SharedEvent(
            id=legacy_evt.id,
            title=legacy_evt.title,
            start_time=legacy_evt.starts_at,
            end_time=legacy_evt.ends_at,
            description=legacy_evt.description,
            location=legacy_evt.location,
        )

    @staticmethod
    def _raise_shared_error(exc: Exception) -> None:
        """Translate legacy/provider errors to shared API exceptions."""
        if isinstance(exc, CalendarNotFoundError):
            raise SharedEventNotFoundError(str(exc)) from exc
        raise SharedCalendarOperationError(str(exc)) from exc

    def list_events(self, start: datetime, end: datetime) -> list[SharedEvent]:
        """Return shared events whose time range intersects [start, end)."""
        if start >= end:
            return []
        try:
            adjusted_end = end - timedelta(microseconds=1)
            legacy_events = self._legacy_client.list_events(start=start, end=adjusted_end, types=None)
        except Exception as exc:
            self._raise_shared_error(exc)
            raise
        return [self._to_shared_event(event) for event in legacy_events]

    def get_event(self, event_id: str) -> SharedEvent:
        """Get one event by id using shared event model."""
        try:
            legacy_evt = self._legacy_client.get_event(event_id=event_id)
        except Exception as exc:
            self._raise_shared_error(exc)
            raise
        return self._to_shared_event(legacy_evt)

    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str | None = None,
    ) -> SharedEvent:
        """Create an event through legacy implementation and return shared model."""
        try:
            legacy_evt = self._legacy_client.create_event(
                title=title,
                starts_at=start_time,
                ends_at=end_time,
                description=description or None,
                location=location,
            )
        except Exception as exc:
            self._raise_shared_error(exc)
            raise
        return self._to_shared_event(legacy_evt)

    def update_event( # noqa: PLR0913
        self,
        event_id: str,
        *,
        title: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        description: str | None = None,
        location: str | None = None) -> SharedEvent:
        """Update event fields and return shared event model."""
        patch = legacy_event.EventPatch(
            title=title,
            starts_at=start_time,
            ends_at=end_time,
            description=description,
            location=location,
        )
        try:
            updated_legacy_evt = self._legacy_client.update_event(event_id=event_id, payload=patch)
        except Exception as exc:
            self._raise_shared_error(exc)
            raise
        return self._to_shared_event(updated_legacy_evt)

    def delete_event(self, event_id: str) -> None:
        """Delete an event through the legacy implementation."""
        try:
            self._legacy_client.delete_event(event_id=event_id)
        except Exception as exc:
            self._raise_shared_error(exc)
            raise


def get_shared_client_impl(*, interactive: bool = False) -> SharedCalendarClient:
    """Return a configured :class:`OutlookSharedClient` instance."""
    return OutlookSharedClient(interactive=interactive)
