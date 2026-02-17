"""Core calendar client contract definitions and factory placeholder."""

from abc import ABC, abstractmethod

from calendar_client_api.event import Event

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
    def create_event(self, event: Event) -> Event:
        """Persist a draft event and return the provider-created instance.

        The input event provides creation fields (for example title/start/end),
        while the returned event reflects provider-assigned fields such as ID.
        """
        raise NotImplementedError

    # TODO: Define additional abstract methods for calendar operations

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        """Delete an event by its ID."""
        raise NotImplementedError


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of a Calendar Client."""
    raise NotImplementedError
