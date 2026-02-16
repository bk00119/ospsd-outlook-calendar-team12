"""Event contract - Core event representation."""

from abc import ABC, abstractmethod
from datetime import datetime


class Event(ABC):
    """Abstract base class representing a calendar event."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the unique identifier of the event."""
        raise NotImplementedError

    @property
    @abstractmethod
    def calendar_id(self) -> str:
        """Return the identifier of the calendar that owns this event."""
        raise NotImplementedError

    @property
    @abstractmethod
    def title(self) -> str:
        """Return the event title/summary."""
        raise NotImplementedError

    @property
    @abstractmethod
    def starts_at(self) -> datetime:
        """Return the event start time (timezone-aware)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ends_at(self) -> datetime:
        """Return the event end time (timezone-aware)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def location(self) -> str | None:
        """Return the event location, if any."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str | None:
        """Return the event description/notes, if any."""
        raise NotImplementedError

# TODO: add more methods

def get_event(event_id: str, raw_data: str) -> Event:
    """Return an instance of an Event.

    Args:
        event_id (str): The unique identifier for the event.
        raw_data (str): Raw provider data used to construct the event.

    Returns:
        Event: An instance conforming to the Event contract.

    Raises:
        NotImplementedError: If the function is not overridden by an implementation.

    """
    raise NotImplementedError
