"""Public exports for the Outlook client implementation package."""

from outlook_client_impl.event_impl import OutlookCalendarEvent as OutlookCalendarEvent
from outlook_client_impl.event_impl import get_event_impl as get_event_impl
from outlook_client_impl.event_impl import register as _register_event
from outlook_client_impl.outlook_impl import OutlookClient as OutlookClient
from outlook_client_impl.outlook_impl import get_client_impl as get_client_impl
from outlook_client_impl.outlook_impl import register as _register_client


def register() -> None:
    """Register the Outlook client and event implementations."""
    _register_client()
    _register_event()


