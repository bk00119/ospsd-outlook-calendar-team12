"""Core calendar client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod
from datetime import datetime

from calendar_client_api.event import Event, EventPatch

__all__ = ["Client", "get_client"]


class Client(ABC):
    """Abstract base class representing a calendar client for event operations."""

    @abstractmethod
    def get_event(self, event_id: str) -> Event:
        """Return an event by its ID."""
        raise NotImplementedError

    @abstractmethod
    def list_events(self) -> list[Event]:
        """Return a list of calendar events."""
        raise NotImplementedError

    @abstractmethod
    def create_event(
        self,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> Event:
        """Create an event from explicit creation fields and return it."""
        raise NotImplementedError

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        """Delete an event by its ID."""
        raise NotImplementedError

    @abstractmethod
    def update_event(self, event_id: str, payload: EventPatch) -> Event:
        """Update an event by its ID with a payload.

        Omitted data fields will remain the same.

        Returns the updated event if successful, otherwise raise an error
        """
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of a Calendar Client."""
    raise NotImplementedError
