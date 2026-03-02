"""Outlook Client Implementation.

This module provides a concrete implementation of the calendar client API using the Outlook API.

The implementation supports multiple authentication modes:
    - Environment variables (for CI/CD environments)
    - Local token file (for development)
    - Interactive OAuth flow (for initial setup)
"""
import asyncio
import datetime
import inspect
import json
import os
from collections.abc import Callable, Coroutine, Mapping
from typing import Any, ClassVar, TypeVar, cast

import calendar_client_api
from calendar_client_api import event
from dotenv import load_dotenv
from kiota_serialization_json.json_serialization_writer import JsonSerializationWriter
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.event import Event as GraphEvent
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.location import Location
from msgraph.graph_service_client import GraphServiceClient

from outlook_client_impl.auth_manager import AuthManager

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
        return self._run_maybe_awaitable(payload)

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

    def _run_maybe_awaitable(self, payload: object) -> object:
        """Resolve coroutine/awaitable values and return plain payload."""
        if inspect.iscoroutine(payload):
            return self._run(cast("Coroutine[Any, Any, object]", payload))
        if inspect.isawaitable(payload):
            async def _await_payload() -> object:
                return await cast("Any", payload)

            return self._run(_await_payload())
        return payload

    def _to_graph_datetime(self, value: datetime.datetime) -> DateTimeTimeZone:
        """Convert a datetime to a Graph DateTimeTimeZone model."""
        if value.tzinfo:
            normalized = value.astimezone(datetime.UTC)
        else:
            normalized = value.replace(tzinfo=datetime.UTC)
        result = DateTimeTimeZone()
        result.date_time = normalized.strftime("%Y-%m-%dT%H:%M:%S")
        result.time_zone = "UTC"
        return result

    def _build_create_payload(
        self,
        title: str,
        starts_at: datetime.datetime,
        ends_at: datetime.datetime,
        location: str | None,
        description: str | None,
    ) -> GraphEvent:
        """Build minimal Graph event model for event creation."""
        payload = GraphEvent()
        payload.subject = title
        payload.start = self._to_graph_datetime(starts_at)
        payload.end = self._to_graph_datetime(ends_at)
        if location and location.strip():
            payload.location = Location()
            payload.location.display_name = location.strip()
        if description and description.strip():
            payload.body = ItemBody()
            payload.body.content_type = BodyType.Text
            payload.body.content = description.strip()
        return payload

    def _extract_event_id(self, created_payload: object, raw_data: str) -> str:
        """Extract created event id from payload or serialized JSON."""
        event_id: object | None = getattr(created_payload, "id", None)
        if isinstance(created_payload, Mapping):
            event_id = cast("Mapping[str, object]", created_payload).get("id")
        if event_id is None:
            try:
                parsed_raw = json.loads(raw_data)
            except json.JSONDecodeError:
                parsed_raw = {}
            if isinstance(parsed_raw, Mapping):
                event_id = cast("Mapping[str, object]", parsed_raw).get("id")

        if not isinstance(event_id, str) or not event_id.strip():
            msg = "Created event payload did not include a valid id."
            raise RuntimeError(msg)
        return event_id.strip()

    def _build_patch_event(self, payload: event.EventPatch) -> GraphEvent:
        """Build a Microsoft Graph PATCH body from an EventPatch.

        Notes:
            - Only fields that are not None are included.
            - start/end are serialized as UTC with timeZone="UTC".
            - body is serialized as plain text (contentType="text").

        Args:
            payload: The partial update payload.

        Returns:
            A GraphEvent instance used as PATCH body.

        """
        ev = GraphEvent()
        empty_payload = True

        if payload.title and payload.title.strip():
            ev.subject = payload.title.strip()
            empty_payload = False

        if payload.description and payload.description.strip():
            b = ItemBody()
            b.content_type = BodyType.Text
            b.content = payload.description.strip()
            ev.body = b
            empty_payload = False

        if payload.location and payload.location.strip():
            loc = Location()
            loc.display_name = payload.location.strip()
            ev.location = loc
            empty_payload = False

        if payload.starts_at is not None:
            ev.start = self._to_graph_datetime(payload.starts_at)
            empty_payload = False

        if payload.ends_at is not None:
            ev.end = self._to_graph_datetime(payload.ends_at)
            empty_payload = False

        if empty_payload:
            msg = "payload must update at least one field."
            raise ValueError(msg)

        return ev

    def _patch_provider_event(
        self,
        *,
        service: object,
        event_id: str,
        body: object,
    ) -> object:
        """Patch an event via Graph builder chain.

        Supports:
        - The Graph builder chain:
          service.me.events.by_event_id(event_id).patch(body)
          (or .update(body) depending on SDK generation)

        Any coroutine/awaitable result will be executed via `_run`.
        """
        me_builder = getattr(service, "me", None)
        events_builder = (
            getattr(me_builder, "events", None) if me_builder is not None else None
        )
        by_event_id = getattr(events_builder, "by_event_id", None)
        if not callable(by_event_id):
            msg = "The service instance does not support event updates."
            raise NotImplementedError(msg)

        request_builder = cast("Callable[[str], object]", by_event_id)(event_id)

        patch_method = getattr(request_builder, "patch", None)
        update_method = getattr(request_builder, "update", None)
        method = patch_method if callable(patch_method) else update_method

        if not callable(method):
            msg = "The Graph request builder does not expose patch() or update()."
            raise NotImplementedError(msg)

        result = cast("Callable[[object], object]", method)(body)
        return self._run_maybe_awaitable(result)


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

    def _fetch_raw_items(self) -> list[object]:
        """Fetch raw event items from the Graph API.

        Raises:
            RuntimeError: If the client has no configured service.
            NotImplementedError: If the service does not support event listing.

        """
        service = getattr(self, "service", None)
        if service is None:
            msg = "Outlook client not configured with a service instance."
            raise RuntimeError(msg)

        me_builder = getattr(service, "me", None)
        events_builder = (
            getattr(me_builder, "events", None) if me_builder is not None else None
        )
        if events_builder is None:
            msg = "The service instance does not support event listing."
            raise NotImplementedError(msg)

        get_method = getattr(events_builder, "get", None)
        if not callable(get_method):
            msg = "The Graph events builder does not expose get()."
            raise NotImplementedError(msg)

        response = cast("Callable[[], object]", get_method)()
        if inspect.iscoroutine(response):
            result = self._run(cast("Coroutine[Any, Any, object]", response))
        elif inspect.isawaitable(response):
            async def _await_list() -> object:
                return await cast("Any", response)

            result = self._run(_await_list())
        else:
            result = response

        return cast("list[object]", getattr(result, "value", None) or [])

    def list_events(
        self,
        *,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        types: list[str] | None = None,
    ) -> list[event.Event]:
        """Return a filtered list of calendar events from Outlook.

        Args:
            start: If provided, only return events that start at or after this time.
            end: If provided, only return events that end at or before this time.
            types: If provided, only return events whose type is in this list
                   (e.g. ``["singleInstance", "occurrence"]``).

        Returns:
            A list of :class:`Event` instances matching the given criteria.

        Raises:
            RuntimeError: If the client has no configured service.

        """
        raw_items = self._fetch_raw_items()

        results: list[event.Event] = []
        for item in raw_items:
            if types is not None:
                if isinstance(item, Mapping):
                    item_type = str(cast("Mapping[str, object]", item).get("type", "") or "")
                else:
                    item_type = str(getattr(item, "type", None) or "")
                if item_type not in types:
                    continue

            if isinstance(item, Mapping):
                item_id = str(cast("Mapping[str, object]", item).get("id", "") or "")
            else:
                item_id = str(getattr(item, "id", None) or "")

            raw_data = self._serialize_provider_payload(item)
            ev = event.get_event(event_id=item_id, raw_data=raw_data)

            if start is not None and ev.starts_at < start:
                continue
            if end is not None and ev.ends_at > end:
                continue

            results.append(ev)
        return results

    def create_event(
        self,
        title: str,
        starts_at: datetime.datetime,
        ends_at: datetime.datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> event.Event:
        """Create a new event in Outlook and return the created event.

        Args:
            title: Event title.
            starts_at: Event start datetime.
            ends_at: Event end datetime.
            location: Optional location.
            description: Optional description.

        Returns:
            An Event reflecting the created resource.

        """
        clean_title = title.strip()
        if not clean_title:
            msg = "title must be a non-empty string."
            raise ValueError(msg)
        if ends_at <= starts_at:
            msg = "ends_at must be after starts_at."
            raise ValueError(msg)

        service = getattr(self, "service", None)
        if service is None:
            msg = "Outlook client not configured with a service instance."
            raise RuntimeError(msg)

        me_builder = getattr(service, "me", None)
        events_builder = getattr(me_builder, "events", None) if me_builder is not None else None
        post_method = getattr(events_builder, "post", None)
        if not callable(post_method):
            msg = "The service instance does not support event creation."
            raise NotImplementedError(msg)

        payload = self._build_create_payload(
            clean_title,
            starts_at,
            ends_at,
            location,
            description,
        )

        created_payload = self._run_maybe_awaitable(post_method(payload))
        if created_payload is None:
            msg = "Outlook event creation returned no payload."
            raise RuntimeError(msg)

        raw_data = self._serialize_provider_payload(created_payload)
        created_event_id = self._extract_event_id(created_payload, raw_data)
        return event.get_event(event_id=created_event_id, raw_data=raw_data)

    def delete_event(self, event_id: str) -> None:
        """Delete a specific event by its ID.

        Args:
            event_id: The unique identifier of the event to delete.

        Raises:
            Exception: If the event cannot be deleted from the Outlook API.

        """
        clean_event_id = event_id.strip()
        if not clean_event_id:
            msg = "event_id must be a non-empty string."
            raise ValueError(msg)

        self._run(self.service.me.events.by_event_id(clean_event_id).delete())

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
        clean_event_id = event_id.strip()
        if not clean_event_id:
            msg = "event_id must be a non-empty string."
            raise ValueError(msg)

        service = getattr(self, "service", None)
        if service is None:
            msg = "Outlook client not configured with a service instance."
            raise RuntimeError(msg)

        patch_event: GraphEvent = self._build_patch_event(payload)

        updated_payload = self._patch_provider_event(
            service=service,
            event_id=clean_event_id,
            body=patch_event,
        )

        # Graph docs specify PATCH can return 200 OK with the updated event.
        # Prefer that payload to avoid an extra GET; fall back if provider returns None.
        if updated_payload is not None:
            raw_data = self._serialize_provider_payload(updated_payload)
            return event.get_event(event_id=clean_event_id, raw_data=raw_data)

        return self.get_event(clean_event_id)



def get_client_impl(*, interactive: bool = False) -> calendar_client_api.Client:
    """Return a configured :class:`OutlookClient` instance."""
    return OutlookClient(interactive=interactive)


def register() -> None:
    """Register the Outlook client implementation with the calendar client API."""
    calendar_client_api.get_client = get_client_impl
