"""Unit tests for OutlookClient.get_event."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest
from calendar_client_api.exceptions import CalendarNotFoundError
from outlook_client_impl.outlook_impl import OutlookClient, get_client_impl

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient


@dataclass
class ServiceStub:
    """Simple service that exposes get_event(event_id)."""

    payload: object
    last_event_id: str | None = None

    def get_event(self, event_id: str) -> object:
        """Return a configured payload for get_event tests."""
        self.last_event_id = event_id
        return self.payload


class AsyncRequestBuilderStub:
    """Graph request-builder stub with async get()."""

    async def get(self) -> object:
        """Return a minimal provider payload."""
        return {
            "subject": "Graph Builder Event",
            "start": {"dateTime": "2026-03-01T10:00:00+00:00"},
            "end": {"dateTime": "2026-03-01T11:00:00+00:00"},
        }


class EventsBuilderStub:
    """Graph events request-builder stub."""

    def __init__(self) -> None:
        """Initialize request id capture for assertions."""
        self.requested_event_id: str | None = None

    def by_event_id(self, event_id: str) -> AsyncRequestBuilderStub:
        """Capture requested id and return request builder."""
        self.requested_event_id = event_id
        return AsyncRequestBuilderStub()


@dataclass
class MeBuilderStub:
    """Graph `me` request-builder stub."""

    events: EventsBuilderStub


@dataclass
class GraphServiceStub:
    """Graph-style service without direct get_event method."""

    me: MeBuilderStub


class SyncRequestBuilderStub:
    """Graph request-builder stub with sync get()."""

    def get(self) -> object:
        """Return a minimal provider payload."""
        return {
            "subject": "Sync Builder Event",
            "start": {"dateTime": "2026-03-01T12:00:00+00:00"},
            "end": {"dateTime": "2026-03-01T13:00:00+00:00"},
        }


class SyncEventsBuilderStub:
    """Graph events request-builder stub that returns sync request builder."""

    def by_event_id(self, event_id: str) -> SyncRequestBuilderStub:
        """Return sync request builder."""
        _ = event_id
        return SyncRequestBuilderStub()


class NoGetRequestBuilderStub:
    """Graph request-builder stub without get()."""


class NoGetEventsBuilderStub:
    """Graph events request-builder that returns unsupported request builder."""

    def by_event_id(self, event_id: str) -> NoGetRequestBuilderStub:
        """Return unsupported request builder."""
        _ = event_id
        return NoGetRequestBuilderStub()


class SerializablePayloadStub:
    """Provider payload stub that mimics Kiota Parsable.serialize()."""

    def serialize(self, writer: object) -> None:
        """Write a minimal event payload via writer."""
        writer_any = cast("Any", writer)
        writer_any.write_str_value("subject", "Serializable Payload Event")


def _client_with_service(service: object) -> OutlookClient:
    """Create a client with an injected stub service to avoid auth in unit tests."""
    return OutlookClient(service=cast("GraphServiceClient", service))


def test_get_event_with_direct_service_payload() -> None:
    """Hydrates an event using service.get_event payload."""
    service = ServiceStub(
        payload={
            "subject": "Architecture Review",
            "start": {"dateTime": "2026-03-01T10:00:00+00:00"},
            "end": {"dateTime": "2026-03-01T10:30:00+00:00"},
            "location": {"displayName": "Room A"},
        },
    )
    client = _client_with_service(service)

    result = client.get_event("  event-123  ")

    assert service.last_event_id == "event-123"
    assert result.id == "event-123"
    assert result.title == "Architecture Review"
    assert result.location == "Room A"


def test_get_event_with_graph_request_builder_payload() -> None:
    """Hydrates an event via Graph-style request builder chain."""
    events_builder = EventsBuilderStub()
    graph_service = GraphServiceStub(me=MeBuilderStub(events=events_builder))

    client = _client_with_service(graph_service)
    result = client.get_event("event-graph")

    assert events_builder.requested_event_id == "event-graph"
    assert result.id == "event-graph"
    assert result.title == "Graph Builder Event"


@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_get_event_rejects_empty_event_id(invalid_id: str) -> None:
    """Raises ValueError when event_id is blank."""
    client = _client_with_service(ServiceStub(payload={}))

    with pytest.raises(ValueError, match="non-empty string"):
        client.get_event(invalid_id)


def test_get_event_raises_when_service_missing() -> None:
    """Raises RuntimeError when service has not been configured."""
    client = object.__new__(OutlookClient)

    with pytest.raises(RuntimeError, match="not configured"):
        client.get_event("event-123")


def test_get_event_raises_when_payload_missing() -> None:
    """Raises RuntimeError when provider payload is missing."""
    service = ServiceStub(payload=None)
    client = _client_with_service(service)

    with pytest.raises(CalendarNotFoundError, match="not found"):
        client.get_event("event-404")


def test_get_event_raises_for_unsupported_service_shape() -> None:
    """Raises NotImplementedError when service lacks get_event and Graph chain."""
    client = _client_with_service(object())

    with pytest.raises(NotImplementedError, match="does not support event retrieval"):
        client.get_event("event-x")


def test_get_event_raises_when_graph_request_builder_has_no_get() -> None:
    """Raises NotImplementedError when Graph request builder misses get()."""
    service = SimpleNamespace(me=SimpleNamespace(events=NoGetEventsBuilderStub()))
    client = _client_with_service(service)

    with pytest.raises(NotImplementedError, match="does not expose get"):
        client.get_event("event-x")


def test_get_event_with_sync_graph_request_builder_payload() -> None:
    """Supports synchronous Graph request-builder get() payloads."""
    service = SimpleNamespace(me=SimpleNamespace(events=SyncEventsBuilderStub()))
    client = _client_with_service(service)

    result = client.get_event("event-sync")

    assert result.id == "event-sync"
    assert result.title == "Sync Builder Event"


def test_get_event_with_string_payload() -> None:
    """Accepts raw JSON string payloads."""
    payload = '{"subject":"String Payload Event"}'
    client = _client_with_service(ServiceStub(payload=payload))

    result = client.get_event("event-str")

    assert result.title == "String Payload Event"


def test_get_event_with_bytes_payload() -> None:
    """Accepts UTF-8 encoded JSON bytes payloads."""
    payload = b'{"subject":"Bytes Payload Event"}'
    client = _client_with_service(ServiceStub(payload=payload))

    result = client.get_event("event-bytes")

    assert result.title == "Bytes Payload Event"


def test_get_event_with_serializable_payload() -> None:
    """Accepts SDK-style payloads that expose serialize()."""
    client = _client_with_service(ServiceStub(payload=SerializablePayloadStub()))

    result = client.get_event("event-serializable")

    assert result.id == "event-serializable"
    assert result.title == "Serializable Payload Event"


def test_get_event_rejects_unsupported_payload_type() -> None:
    """Raises TypeError when provider payload shape is unsupported."""
    client = _client_with_service(ServiceStub(payload=123))

    with pytest.raises(TypeError, match="Event payload must be JSON string"):
        client.get_event("event-bad")


def test_get_client_impl_returns_outlook_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory returns an OutlookClient instance."""
    fake_service = cast("GraphServiceClient", object())

    monkeypatch.setattr(OutlookClient, "CLIENT_ID", "test-client-id")
    monkeypatch.setattr(
        OutlookClient,
        "AUTHORITY",
        "https://login.microsoftonline.com/consumers",
    )

    def _fake_get_graph_client(self: object) -> GraphServiceClient:
        _ = self
        return fake_service

    monkeypatch.setattr(
        "outlook_client_impl.outlook_impl.AuthManager.get_graph_client",
        _fake_get_graph_client,
    )

    client = get_client_impl(interactive=False)

    assert isinstance(client, OutlookClient)
    assert client.service is fake_service
