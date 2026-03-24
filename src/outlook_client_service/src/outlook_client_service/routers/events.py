"""Event routes for the Outlook client service."""

from http import HTTPStatus
from typing import Annotated

from calendar_client_api.event import Event, EventPatch
from fastapi import APIRouter, Depends, HTTPException, status
from outlook_client_impl.outlook_impl import OutlookClient

from outlook_client_service.dependencies import get_outlook_client
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


@router.get("/")
def list_events() -> list[EventResponse]:
    """List events."""
    return []


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_event(
    event: EventCreateRequest,
    client: Annotated[OutlookClient, Depends(get_outlook_client)],
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
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=f"Failed to create event: {e}") from e
    return _to_event_response(created_event)


@router.patch("/{event_id}")
def update_event(
    event_id: str,
    event: EventUpdateRequest,
    client: Annotated[OutlookClient, Depends(get_outlook_client)],
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
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=f"Failed to update event: {e}") from e
    return _to_event_response(updated_event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: str, client: Annotated[OutlookClient, Depends(get_outlook_client)]) -> None:
    """Delete an event."""
    try:
        client.delete_event(event_id=event_id)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_GATEWAY, detail=f"Failed to delete event: {e}") from e
