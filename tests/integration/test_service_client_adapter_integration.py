"""Integration tests for ServiceClientAdapter over generated HTTP client calls."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus

import httpx
import pytest
from calendar_client_api.event import EventPatch
from outlook_client_service_api_client.client import Client as GeneratedClient
from outlook_service_client_adapter.adapter import ServiceClientAdapter

pytestmark = [pytest.mark.integration, pytest.mark.circleci]


def _build_adapter(transport: httpx.MockTransport) -> ServiceClientAdapter:
    """Create an adapter backed by a generated client that uses MockTransport."""
    generated = GeneratedClient(base_url="http://testserver")
    generated.set_httpx_client(
        httpx.Client(
            base_url="http://testserver",
            transport=transport,
        ),
    )
    return ServiceClientAdapter(generated)


def test_create_event_over_generated_client() -> None:
    """Create event via adapter and verify request/response mapping."""
    starts_at = datetime(2026, 4, 3, 14, 0, tzinfo=UTC)
    ends_at = datetime(2026, 4, 3, 15, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/events/"
        payload = request.read().decode("utf-8")
        assert '"title":"Adapter create"' in payload
        assert '"location":"Room 101"' in payload
        return httpx.Response(
            status_code=HTTPStatus.CREATED,
            json={
                "id": "evt-create-1",
                "title": "Adapter create",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "location": "Room 101",
                "description": "create integration",
            },
        )

    adapter = _build_adapter(httpx.MockTransport(handler))
    event = adapter.create_event(
        title="Adapter create",
        starts_at=starts_at,
        ends_at=ends_at,
        location="Room 101",
        description="create integration",
    )

    assert event.id == "evt-create-1"
    assert event.title == "Adapter create"
    assert event.starts_at == starts_at
    assert event.ends_at == ends_at
    assert event.location == "Room 101"
    assert event.description == "create integration"


def test_get_event_over_generated_client() -> None:
    """Get event via adapter and verify path mapping."""
    starts_at = datetime(2026, 4, 3, 16, 0, tzinfo=UTC)
    ends_at = datetime(2026, 4, 3, 17, 0, tzinfo=UTC)
    event_id = "evt-get-1"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/events/{event_id}"
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json={
                "id": event_id,
                "title": "Adapter get",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "location": "Room 102",
                "description": "get integration",
            },
        )

    adapter = _build_adapter(httpx.MockTransport(handler))
    event = adapter.get_event(event_id)

    assert event.id == event_id
    assert event.title == "Adapter get"
    assert event.starts_at == starts_at
    assert event.ends_at == ends_at
    assert event.location == "Room 102"
    assert event.description == "get integration"


def test_list_events_over_generated_client() -> None:
    """List events via adapter and verify query mapping for start/end."""
    start_filter = datetime(2026, 4, 3, 12, 0, tzinfo=UTC)
    end_filter = datetime(2026, 4, 3, 20, 0, tzinfo=UTC)
    starts_at = datetime(2026, 4, 3, 18, 0, tzinfo=UTC)
    ends_at = datetime(2026, 4, 3, 19, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/events/"
        assert request.url.params.get("start") == start_filter.isoformat()
        assert request.url.params.get("end") == end_filter.isoformat()
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json=[
                {
                    "id": "evt-list-1",
                    "title": "Adapter list",
                    "starts_at": starts_at.isoformat(),
                    "ends_at": ends_at.isoformat(),
                    "location": "Room 103",
                    "description": "list integration",
                },
            ],
        )

    adapter = _build_adapter(httpx.MockTransport(handler))
    events = adapter.list_events(start=start_filter, end=end_filter, types=["singleInstance"])

    assert len(events) == 1
    assert events[0].id == "evt-list-1"
    assert events[0].title == "Adapter list"


def test_update_event_over_generated_client() -> None:
    """Update event via adapter and verify request payload mapping."""
    starts_at = datetime(2026, 4, 3, 21, 0, tzinfo=UTC)
    ends_at = datetime(2026, 4, 3, 22, 0, tzinfo=UTC)
    event_id = "evt-update-1"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == f"/events/{event_id}"
        payload = request.read().decode("utf-8")
        assert '"title":"Adapter update"' in payload
        assert '"location":"Room 104"' in payload
        return httpx.Response(
            status_code=HTTPStatus.OK,
            json={
                "id": event_id,
                "title": "Adapter update",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "location": "Room 104",
                "description": "update integration",
            },
        )

    adapter = _build_adapter(httpx.MockTransport(handler))
    event = adapter.update_event(
        event_id,
        EventPatch(
            title="Adapter update",
            starts_at=starts_at,
            ends_at=ends_at,
            location="Room 104",
            description="update integration",
        ),
    )

    assert event.id == event_id
    assert event.title == "Adapter update"
    assert event.location == "Room 104"


def test_delete_event_over_generated_client() -> None:
    """Delete event via adapter and verify request path mapping."""
    event_id = "evt-delete-1"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == f"/events/{event_id}"
        return httpx.Response(status_code=HTTPStatus.NO_CONTENT)

    adapter = _build_adapter(httpx.MockTransport(handler))
    adapter.delete_event(event_id)
