"""Shared calendar API implementation backed by the existing Outlook client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

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
    import datetime

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

    def list_events(self, start: datetime.datetime, end: datetime.datetime) -> list[SharedEvent]:
        """Return shared events whose time range intersects [start, end)."""
        try:
            legacy_events = self._legacy_client.list_events(start=start, end=end, types=None)
        except Exception as exc:  # noqa: BLE001
            self._raise_shared_error(exc)
        return [self._to_shared_event(event) for event in legacy_events]

    def get_event(self, event_id: str) -> SharedEvent:
        """Get one event by id using shared event model."""
        try:
            legacy_evt = self._legacy_client.get_event(event_id=event_id)
        except Exception as exc:  # noqa: BLE001
            self._raise_shared_error(exc)
        return self._to_shared_event(legacy_evt)

    def create_event(
        self,
        title: str,
        start: datetime.datetime,
        end: datetime.datetime,
        description: str = "",
        location: str | None = None,
    ) -> SharedEvent:
        """Create an event through legacy implementation and return shared model."""
        try:
            legacy_evt = self._legacy_client.create_event(
                title=title,
                starts_at=start,
                ends_at=end,
                description=description or None,
                location=location,
            )
        except Exception as exc:  # noqa: BLE001
            self._raise_shared_error(exc)
        return self._to_shared_event(legacy_evt)

    def update_event(self, event_id: str, **kwargs: Any) -> SharedEvent:  # noqa: ANN401
        """Update event fields and return shared event model."""
        allowed = {"title", "start_time", "end_time", "description", "location"}
        unknown = set(kwargs) - allowed
        if unknown:
            msg = f"Unsupported update fields: {sorted(unknown)}"
            raise ValueError(msg)

        patch = legacy_event.EventPatch(
            title=cast("str | None", kwargs.get("title")),
            starts_at=cast("datetime.datetime | None", kwargs.get("start_time")),
            ends_at=cast("datetime.datetime | None", kwargs.get("end_time")),
            description=cast("str | None", kwargs.get("description")),
            location=cast("str | None", kwargs.get("location")),
        )
        try:
            updated_legacy_evt = self._legacy_client.update_event(event_id=event_id, payload=patch)
        except Exception as exc:  # noqa: BLE001
            self._raise_shared_error(exc)
        return self._to_shared_event(updated_legacy_evt)

    def delete_event(self, event_id: str) -> None:
        """Delete an event through the legacy implementation."""
        try:
            self._legacy_client.delete_event(event_id=event_id)
        except Exception as exc:  # noqa: BLE001
            self._raise_shared_error(exc)


def get_shared_client_impl(*, interactive: bool = False) -> SharedCalendarClient:
    """Return a configured :class:`OutlookSharedClient` instance."""
    return OutlookSharedClient(interactive=interactive)
