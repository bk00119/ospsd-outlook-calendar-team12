"""Service client adapter — implements the Client ABC via the auto-generated service client."""

from dataclasses import dataclass
from datetime import datetime

from calendar_client_api.client import Client
from calendar_client_api.event import Event, EventPatch
from outlook_client_service_client.api.events import (
    create_event_events_post,
    delete_event_events_event_id_delete,
    list_events_events_get,
    update_event_events_event_id_patch,
)
from outlook_client_service_client.client import Client as GeneratedClient
from outlook_client_service_client.models.event_create_request import EventCreateRequest
from outlook_client_service_client.models.event_response import EventResponse
from outlook_client_service_client.models.event_update_request import EventUpdateRequest
from outlook_client_service_client.models.http_validation_error import HTTPValidationError
from outlook_client_service_client.types import Unset


@dataclass(frozen=True)
class AdapterEvent(Event):
    """Concrete Event implementation used by the adapter."""

    _id: str
    _title: str
    _starts_at: datetime
    _ends_at: datetime
    _location: str | None
    _description: str | None

    @property
    def id(self) -> str:
        """Return the unique identifier of the event."""
        return self._id

    @property
    def title(self) -> str:
        """Return the event title."""
        return self._title

    @property
    def starts_at(self) -> datetime:
        """Return the event start timestamp."""
        return self._starts_at

    @property
    def ends_at(self) -> datetime:
        """Return the event end timestamp."""
        return self._ends_at

    @property
    def location(self) -> str | None:
        """Return the event location."""
        return self._location

    @property
    def description(self) -> str | None:
        """Return the event description."""
        return self._description


class ServiceClientAdapter(Client):
    """Adapt the auto-generated HTTP client to the Client ABC.

    Each method delegates to the corresponding auto-generated function,
    translating between the ABC's interface and the generated API.
    """

    def __init__(self, generated_client: GeneratedClient) -> None:
        """Initialize the adapter with an instance of the generated client."""
        self._client = generated_client

    @staticmethod
    def _unset_to_none(value: str | None | Unset) -> str | None:
        """Convert generated optional values into plain optional strings."""
        if isinstance(value, Unset):
            return None
        return value

    @classmethod
    def _event_from_response(cls, response: EventResponse) -> Event:
        """Map generated EventResponse to the API Event type."""
        return AdapterEvent(
            _id=response.id,
            _title=response.title,
            _starts_at=response.starts_at,
            _ends_at=response.ends_at,
            _location=cls._unset_to_none(response.location),
            _description=cls._unset_to_none(response.description),
        )

    def delete_event(self, event_id: str) -> None:
        """Delete an event by its ID."""
        delete_event_events_event_id_delete.sync(
            event_id=event_id,
            client=self._client,
        )

    def get_event(self, event_id: str) -> Event:
        """Return an event by its ID."""
        raise NotImplementedError

    def list_events(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        types: list[str] | None = None,
    ) -> list[Event]:
        """Return a list of calendar events, with optional filters."""
        result = list_events_events_get.sync(
            client=self._client,
            start=start,
            end=end,
        )
        if result is None:
            return []
        if isinstance(result, HTTPValidationError):
            msg = f"list_events validation failed: {result.to_dict()}"
            raise TypeError(msg)
        return [self._event_from_response(ev) for ev in result]

    def create_event(
        self,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> Event:
        """Create an event and return it."""
        body = EventCreateRequest(
            title=title,
            starts_at=starts_at,
            ends_at=ends_at,
            location=location,
            description=description,
        )
        result = create_event_events_post.sync(
            client=self._client,
            body=body,
        )
        if result is None:
            msg = "create_event returned no response payload."
            raise RuntimeError(msg)
        if isinstance(result, HTTPValidationError):
            msg = f"create_event validation failed: {result.to_dict()}"
            raise TypeError(msg)
        return self._event_from_response(result)

    def update_event(self, event_id: str, payload: EventPatch) -> Event:
        """Update an event by its ID with a payload."""
        body = EventUpdateRequest(
            title=payload.title,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            location=payload.location,
            description=payload.description,
        )
        result = update_event_events_event_id_patch.sync(
            client=self._client,
            event_id=event_id,
            body=body,
        )
        if result is None:
            msg = "update_event returned no response payload."
            raise RuntimeError(msg)
        if isinstance(result, HTTPValidationError):
            msg = f"update_event validation failed: {result.to_dict()}"
            raise TypeError(msg)
        return self._event_from_response(result)

