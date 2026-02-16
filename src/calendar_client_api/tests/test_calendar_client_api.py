"""Tests for the calendar client API abstract base classes.

This module contains unit tests that verify the contracts and behavior
of the calendar_client_api.Client and calendar_client_api.Event abstractions.
These tests use mocks to demonstrate how implementations should behave
and serve as documentation for the expected API contracts.
"""

from unittest.mock import Mock

from calendar_client_api import Client, Event


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
