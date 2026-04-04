"""Event routes for the Outlook client service."""

from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from calendar_client_api.client import Client
from calendar_client_api.event import Event, EventPatch
from calendar_client_api.exceptions import (
    CalendarAuthError,
    CalendarError,
    CalendarNotFoundError,
    CalendarServiceError,
    CalendarValidationError,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status

from outlook_client_service.dependencies import get_calendar_client
from outlook_client_service.schemas.event import (
    EventCreateRequest,
    EventResponse,
    EventUpdateRequest,
)

router = APIRouter()


def _to_event_response(event: Event) -> EventResponse:
    """Convert a calendar-client event object to an EventResponse."""
    return EventResponse(
        id=event.id,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        location=event.location,
        description=event.description,
    )


def _raise_http_from_domain(exc: Exception, default_message: str) -> None:
    """Translate typed domain exceptions to HTTP status codes."""
    if isinstance(exc, CalendarValidationError):
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, CalendarNotFoundError):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CalendarAuthError):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=str(exc)) from exc
    if isinstance(exc, CalendarServiceError):
        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=str(exc)) from exc
    raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=f"{default_message}: {exc}") from exc


@router.get("/")
def list_events(
    client: Annotated[Client, Depends(get_calendar_client)],
    start: datetime | None = None,
    end: datetime | None = None,
    types: Annotated[list[str] | None, Query()] = None,
) -> list[EventResponse]:
    """List calendar events, optionally filtered by start and end time."""
    try:
        events = client.list_events(start=start, end=end, types=types)
    except (CalendarError, RuntimeError) as e:
        _raise_http_from_domain(e, "Failed to list events")
    return [_to_event_response(ev) for ev in events]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_event(
    event: EventCreateRequest,
    client: Annotated[Client, Depends(get_calendar_client)],
) -> EventResponse:
    """Create a new event."""
    try:
        created_event = client.create_event(
            title=event.title,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            location=event.location,
            description=event.description,
        )
    except (CalendarError, RuntimeError) as e:
        _raise_http_from_domain(e, "Failed to create event")
    return _to_event_response(created_event)


@router.patch("/{event_id}")
def update_event(
    event_id: str,
    event: EventUpdateRequest,
    client: Annotated[Client, Depends(get_calendar_client)],
) -> EventResponse:
    """Update an existing event record partially."""
    patch = EventPatch(
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        location=event.location,
        description=event.description,
    )
    try:
        updated_event = client.update_event(event_id=event_id, payload=patch)
    except (CalendarError, RuntimeError) as e:
        _raise_http_from_domain(e, "Failed to update event")
    return _to_event_response(updated_event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: str, client: Annotated[Client, Depends(get_calendar_client)]) -> None:
    """Delete an event."""
    try:
        client.delete_event(event_id=event_id)
    except (CalendarError, RuntimeError) as e:
        _raise_http_from_domain(e, "Failed to delete event")


@router.get("/{event_id}")
def get_event(event_id: str, client: Annotated[Client, Depends(get_calendar_client)]) -> EventResponse:
    """Get an event by ID."""
    try:
        event = client.get_event(event_id=event_id)
    except (CalendarError, RuntimeError) as e:
        _raise_http_from_domain(e, "Failed to get event")
    return _to_event_response(event)
