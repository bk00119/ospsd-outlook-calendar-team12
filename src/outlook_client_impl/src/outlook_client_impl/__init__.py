"""Public exports for the Outlook client implementation package."""

from outlook_client_impl.event_impl import (
    OutlookCalendarEvent,
    get_event_impl,
)
from outlook_client_impl.event_impl import (
    register as _register_event,
)
from outlook_client_impl.outlook_impl import (
    OutlookClient,
    get_client_impl,
)
from outlook_client_impl.outlook_impl import (
    register as _register_client,
)

__all__ = [
    "OutlookCalendarEvent",
    "OutlookClient",
    "get_client_impl",
    "get_event_impl",
    "register",
]


def register() -> None:
    """Register the Outlook client and event implementations."""
    _register_client()
    _register_event()


# Dependency Injection happens at import time
register()
