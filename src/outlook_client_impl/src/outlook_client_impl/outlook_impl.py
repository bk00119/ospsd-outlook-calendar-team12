"""Outlook Client Implementation.

This module provides a concrete implementation of the calendar client API using the Outlook API.

The implementation supports multiple authentication modes:
    - Environment variables (for CI/CD environments)
    - Local token file (for development)
    - Interactive OAuth flow (for initial setup)
"""
import os
from pathlib import Path

import calendar_client_api
from calendar_client_api import event

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # If python-dotenv is not available, check if .env file exists
    # and manually load it
    env_path = Path(".env")
    if env_path.exists():
        with env_path.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

class OutlookClient(calendar_client_api.Client):
    """Concrete implementation of the Client abstraction using Outlook API."""

    # TODO: modify __init__ to work with Outlook API authentication and service setup
    def __init__(self, service: None = None, *, interactive: bool = False) -> None:
         """Initialize the OutlookClient, handling authentication."""
        # TODO: Implement authentication and service setup here

    def get_event(self, event_id: str) -> event.Event:
        """Retrieve a specific event by its ID.

        Args:
            event_id: The unique identifier of the event to retrieve.

        Returns:
            An Event object containing the event data.

        Raises:
            Exception: If the event cannot be retrieved from the Outlook API.

        """
        # TODO: implement this
        err_msg = "OutlookClient.get_event is not yet implemented."
        raise NotImplementedError(err_msg)

    def list_events(self) -> list[event.Event]:
        """Return a list of calendar events from Outlook."""
        err_msg = "OutlookClient.list_events is not yet implemented."
        raise NotImplementedError(err_msg)

    def create_event(self, event_data: event.Event) -> event.Event:
        """Create a new event in Outlook and return the created event.

        Args:
            event_data: The event data to persist to Outlook.

        Returns:
            An Event reflecting the created resource.

        """
        # TODO: integrate with Outlook Graph API to create the event
        err_msg = "OutlookClient.create_event is not yet implemented."
        raise NotImplementedError(err_msg)

    def delete_event(self, event_id: str) -> None:
        """Delete a specific event by its ID.

        Args:
            event_id: The unique identifier of the event to delete.

        Raises:
            Exception: If the event cannot be deleted from the Outlook API.

        """
        # TODO: implementation for deleting an event using the Outlook API
        err_msg = "OutlookClient.delete_event is not yet implemented."
        raise NotImplementedError(err_msg)

    def update_event(self, event_id: str, payload: event.EventPatch) -> event.Event:
        """Update an event by id in Outlook and return the updated event.

        Args:
            event_id: The id of the event that needs to be updated.
            payload: The patch of fields that needs to be updated.
                    Missing fields will remain the same.

        Returns:
            The updated event.

        Raises:
            Exception: If the updating fails for reasons like wrong event id.

        """
        # TODO: integrate with Outlook Graph API to update the event
        err_msg = "OutlookClient.update_event is not yet implemented."
        raise NotImplementedError(err_msg)


def get_client_impl(*, interactive: bool = False) -> calendar_client_api.Client:
    """Return a configured :class:`OutlookClient` instance."""
    return OutlookClient(interactive=interactive)


def register() -> None:
    """Register the Outlook client implementation with the calendar client API."""
    calendar_client_api.get_client = get_client_impl
