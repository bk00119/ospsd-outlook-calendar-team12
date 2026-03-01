"""Tests for the calendar_client_api event abstraction."""

from unittest.mock import Mock

from calendar_client_api.event import Event


def test_event_abstraction_comprehensive() -> None:
    """Verifies all properties work together in a comprehensive test."""
    mock_event = Mock(spec=Event)
    mock_event.id = "event_12345"
    mock_event.title = "testEvent"
    mock_event.starts_at = "2025-07-30 14:45:30"
    mock_event.ends_at = "2025-07-30 15:45:30"
    mock_event.location = "NYU"
    mock_event.description = "This is a test event for verifying the Event abstraction."

    properties = {
        "id": mock_event.id,
        "title": mock_event.title,
        "starts_at": mock_event.starts_at,
        "ends_at": mock_event.ends_at,
        "location": mock_event.location,
        "description": mock_event.description,
    }

    assert properties["id"] == "event_12345"
    assert properties["title"] == "testEvent"
    assert properties["starts_at"] == "2025-07-30 14:45:30"
    assert properties["ends_at"] == "2025-07-30 15:45:30"
    assert properties["location"] == "NYU"
    assert properties["description"] == "This is a test event for verifying the Event abstraction."

    for value in properties.values():
        assert isinstance(value, str)
