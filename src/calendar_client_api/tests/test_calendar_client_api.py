"""Tests for the calendar client API abstract base classes.

This module contains unit tests that verify the contracts and behavior
of the calendar_client_api.Client and calendar_client_api.Event abstractions.
These tests use mocks to demonstrate how implementations should behave
and serve as documentation for the expected API contracts.
"""

import datetime
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
    """Verifies the contract for the `list_events` method (no filters)."""
    mock_client = Mock(spec=Client)
    mock_client.list_events.return_value = []

    assert mock_client.list_events() == []


def test_client_list_events_with_filters() -> None:
    """Verifies the contract for `list_events` with start, end, and types filters."""
    mock_event = Mock(spec=Event)
    mock_event.id = "filtered_event_id"

    mock_client = Mock(spec=Client)
    mock_client.list_events.return_value = [mock_event]

    start = datetime.datetime(2026, 3, 1, 9, 0, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2026, 3, 1, 18, 0, tzinfo=datetime.timezone.utc)

    results = mock_client.list_events(start=start, end=end, types=["singleInstance"])

    mock_client.list_events.assert_called_once_with(
        start=start, end=end, types=["singleInstance"],
    )
    assert len(results) == 1
    assert results[0].id == "filtered_event_id"


def test_client_create_event() -> None:
    """Verifies and documents the contract for the `create_event` method."""
    # ARRANGE
    mock_event = Mock(spec=Event)
    mock_event.id = "new_event_id"

    mock_client = Mock(spec=Client)
    mock_client.create_event.return_value = mock_event

    # ACT
    created_event = mock_client.create_event(event=mock_event)

    # ASSERT
    mock_client.create_event.assert_called_once_with(event=mock_event)
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

