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

    # TODO: Define additional abstract methods for calendar operations


def get_client(*, interactive: bool = False) -> Client:
    """Return an instance of a Calendar Client."""
    raise NotImplementedError
