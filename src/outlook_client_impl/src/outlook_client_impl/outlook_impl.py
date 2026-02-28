"""Outlook Client Implementation.

This module provides a concrete implementation of the calendar client API using the Outlook API.

The implementation supports multiple authentication modes:
    - Environment variables (for CI/CD environments)
    - Local token file (for development)
    - Interactive OAuth flow (for initial setup)
"""
import asyncio
import inspect
import json
import os
from collections.abc import Callable, Coroutine, Mapping
from typing import Any, ClassVar, TypeVar, cast

import calendar_client_api
from calendar_client_api import event
from dotenv import load_dotenv
from kiota_serialization_json.json_serialization_writer import JsonSerializationWriter
from msgraph.graph_service_client import GraphServiceClient

from .auth_manager import AuthManager

T = TypeVar("T")

load_dotenv()


class OutlookClient(calendar_client_api.Client):
    """Concrete implementation of the Client abstraction using Outlook API."""

    CLIENT_ID: ClassVar[str | None] = os.environ.get("AZURE_CLIENT_ID")
    AUTHORITY: ClassVar[str | None] = os.environ.get("AZURE_AUTHORITY")
    SCOPES: ClassVar[list[str]] = ["User.Read", "Calendars.ReadWrite"]
    NESTED_SYNC_ERR: ClassVar[str] = \
        "OutlookClient sync methods cannot run inside an existing asyncio loop."
    MISSING_CLIENT_ID_ERR: ClassVar[str] = \
        "Missing AZURE_CLIENT_ID. Set it in .env or environment variables."
    MISSING_AUTHORITY_ERR: ClassVar[str] = \
        "Missing AZURE_AUTHORITY. Set it in .env or environment variables."

    def __init__(
        self,
        service: GraphServiceClient | None = None,
        *,
        interactive: bool = False,
    ) -> None:
        """Initialize the OutlookClient, handling authentication."""
        if service is not None:
            self.service = service
            return  # Skip auth if service is provided

        client_id = self.CLIENT_ID
        authority = self.AUTHORITY
        if not client_id:
            raise RuntimeError(self.MISSING_CLIENT_ID_ERR)
        if not authority:
            raise RuntimeError(self.MISSING_AUTHORITY_ERR)

        auth = AuthManager(
            client_id=client_id,
            authority=authority,
            scopes=self.SCOPES,
            interactive=interactive,
        )
        self.service = auth.get_graph_client()


    # Helper to run async Graph calls from sync interface methods.
    def _run(self, coro: Coroutine[Any, Any, T]) -> T:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            coro.close()
            raise RuntimeError(self.NESTED_SYNC_ERR)
        return asyncio.run(coro)

    def _fetch_provider_payload(self, *, service: object, event_id: str) -> object:
        """Fetch payload from either direct service method or Graph builder chain."""
        direct_get_event = getattr(service, "get_event", None)
        if callable(direct_get_event):
            typed_get_event = cast("Callable[[str], object]", direct_get_event)
            return typed_get_event(event_id)

        me_builder = getattr(service, "me", None)
        events_builder = (
            getattr(me_builder, "events", None) if me_builder is not None else None
        )
        by_event_id = getattr(events_builder, "by_event_id", None)
        if not callable(by_event_id):
            msg = "The service instance does not support event retrieval."
            raise NotImplementedError(msg)

        request_builder = cast("Callable[[str], object]", by_event_id)(event_id)
        get_method = getattr(request_builder, "get", None)
        if not callable(get_method):
            msg = "The Graph request builder does not expose get()."
            raise NotImplementedError(msg)

        payload = cast("Callable[[], object]", get_method)()
        if inspect.iscoroutine(payload):
            return self._run(cast("Coroutine[Any, Any, object]", payload))
        if inspect.isawaitable(payload):
            async def _await_payload() -> object:
                return await cast("Any", payload)

            return self._run(_await_payload())
        return payload

    def _serialize_provider_payload(self, payload: object) -> str:
        """Serialize provider payload into JSON string expected by event factory."""
        if isinstance(payload, str):
            return payload
        if isinstance(payload, bytes):
            return payload.decode("utf-8")
        if isinstance(payload, Mapping):
            typed_payload = cast("Mapping[str, object]", payload)
            return json.dumps(dict(typed_payload), default=str)
        serialize = getattr(payload, "serialize", None)
        if callable(serialize):
            writer = JsonSerializationWriter()
            cast("Callable[[JsonSerializationWriter], None]", serialize)(writer)
            return writer.get_serialized_content().decode("utf-8")

        msg = "Event payload must be JSON string, bytes, or mapping."
        raise TypeError(msg)

    def get_event(self, event_id: str) -> event.Event:
        """Retrieve a specific event by its ID.

        Args:
            event_id: The unique identifier of the event to retrieve.

        Returns:
            An Event object containing the event data.

        Raises:
            Exception: If the event cannot be retrieved from the Outlook API.

        """
        clean_event_id = event_id.strip()
        if not clean_event_id:
            msg = "event_id must be a non-empty string."
            raise ValueError(msg)

        service = getattr(self, "service", None)
        if service is None:
            msg = "Outlook client not configured with a service instance."
            raise RuntimeError(msg)

        payload = self._fetch_provider_payload(service=service, event_id=clean_event_id)

        if payload is None:
            msg = f"Event '{clean_event_id}' was not found."
            raise RuntimeError(msg)

        raw_data = self._serialize_provider_payload(payload)
        return event.get_event(event_id=clean_event_id, raw_data=raw_data)

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
        if not event_id or not event_id.strip():
            msg = "event_id must be a non-empty string."
            raise ValueError(msg)

        # Temporary placeholder until integration is implemented
        # TODO: integrate with Outlook Graph API to delete the event once service setup is done
        service = getattr(self, "service", None)
        if service is None:
            msg = "Outlook client not configured with a service instance."
            raise RuntimeError(msg)

        delete_function = getattr(service, "delete_event", None)
        if delete_function is None:
            msg = "The service instance does not have a delete_event method."
            raise NotImplementedError(msg)

        delete_function(event_id)

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
