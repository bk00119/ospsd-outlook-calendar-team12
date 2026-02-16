"""Public export surface for ``calendar_client_api``."""

from calendar_client_api import event
from calendar_client_api.client import Client, get_client
from calendar_client_api.event import Event, get_event

__all__ = ["Client", "Event", "event", "get_client", "get_event"]
