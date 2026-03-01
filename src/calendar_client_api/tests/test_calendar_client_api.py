"""Tests for the calendar client API abstract base classes.

This module contains unit tests that verify the contracts and behavior
of the calendar_client_api.Client and calendar_client_api.Event abstractions.
These tests use mocks to demonstrate how implementations should behave
and serve as documentation for the expected API contracts.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

from calendar_client_api import Client, Event, EventPatch


def test_client_get_event() -> None:
    """Verifies and demonstrates the contract for the `get_event` method."""
    # ARRANGE
    mock_event = Mock(spec=Event)
    mock_event.id = "specific_event_id"

    mock_client = Mock(spec=Client)
    mock_client.get_event.return_value = mock_event

    # ACT
    retrieved_event = mock_client.get_event(event_id="specific_event_id")

    # ASSERT
    mock_client.get_event.assert_called_once_with(event_id="specific_event_id")
    assert retrieved_event.id == "specific_event_id"


def test_client_list_events() -> None:
    """Verifies the contract for the `list_events` method."""
    mock_client = Mock(spec=Client)
    mock_client.list_events.return_value = []

    assert mock_client.list_events() == []


def test_client_create_event() -> None:
    """Verifies and documents the contract for the `create_event` method."""
    # ARRANGE
    mock_event = Mock(spec=Event)
    mock_event.id = "new_event_id"

    mock_client = Mock(spec=Client)
    mock_client.create_event.return_value = mock_event

    # ACT
    start = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    end = datetime(2026, 3, 1, 11, 0, tzinfo=UTC)
    created_event = mock_client.create_event(
        title="Planning Session",
        starts_at=start,
        ends_at=end,
        location="Room A",
        description="Discuss roadmap.",
    )

    # ASSERT
    mock_client.create_event.assert_called_once_with(
        title="Planning Session",
        starts_at=start,
        ends_at=end,
        location="Room A",
        description="Discuss roadmap.",
    )
    assert created_event.id == "new_event_id"


def test_client_delete_event() -> None:
    """Verifies and documents the contract for the `delete_event` method."""
    # ARRANGE
    mock_client = Mock(spec=Client)

    # ACT
    mock_client.delete_event(event_id="event_to_delete")

    # ASSERT
    mock_client.delete_event.assert_called_once_with(event_id="event_to_delete")


def test_client_update_event() -> None:
    """Verifies and documents the contract for the `update_event` method."""
    # ARRANGE
    mock_event = Mock(spec=Event)
    mock_event.id = "event-123"
    mock_event.title = "second meeting"

    mock_patch = Mock(spec=EventPatch)
    mock_patch.title = "second meeting"

    mock_client = Mock(spec=Client)
    mock_client.update_event.return_value = mock_event

    # ACT
    updated_event = mock_client.update_event(event_id="event-123", payload=mock_patch)

    # ASSERT
    mock_client.update_event.assert_called_once_with(event_id="event-123", payload=mock_patch)
    assert updated_event.id == "event-123"
    assert updated_event.title == "second meeting"
