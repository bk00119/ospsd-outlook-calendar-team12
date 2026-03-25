"""Service client adapter — implements the Client ABC via the auto-generated service client."""

from datetime import datetime

from calendar_client_api.client import Client
from calendar_client_api.event import Event, EventPatch
from outlook_client_service_client.api.events import delete_event_events_event_id_delete
from outlook_client_service_client.client import Client as GeneratedClient


class ServiceClientAdapter(Client):
    """Adapt the auto-generated HTTP client to the Client ABC.

    Each method delegates to the corresponding auto-generated function,
    translating between the ABC's interface and the generated API.
    """

    def __init__(self, generated_client: GeneratedClient) -> None:
        """Initialize the adapter with an instance of the generated client."""
        self._client = generated_client

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
        raise NotImplementedError

    def create_event(
        self,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> Event:
        """Create an event and return it."""
        raise NotImplementedError

    def update_event(self, event_id: str, payload: EventPatch) -> Event:
        """Update an event by its ID with a payload."""
        raise NotImplementedError
