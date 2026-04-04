"""Contract-style test for OutlookClient.delete_event."""

from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from outlook_client_impl.outlook_impl import OutlookClient


def test_outlook_client_delete_event_success() -> None:
    """Verifies delete_event calls the Graph delete request for the given ID."""
    service = Mock()
    request_builder = Mock()
    request_builder.delete = AsyncMock(return_value=None)

    service.me.events.by_event_id.return_value = request_builder

    client = OutlookClient(service=service)

    def _fake_run(coro: Coroutine[Any, Any, Any]) -> None:
        # Close the coroutine returned by AsyncMock.delete() to avoid
        # "coroutine was never awaited" warnings.
        coro.close()

    with patch.object(client, "_run", side_effect=_fake_run) as run_mock:
        event_id = "test-event-id"
        client.delete_event(event_id)

        service.me.events.by_event_id.assert_called_once_with(event_id)
        request_builder.delete.assert_called_once_with()
        run_mock.assert_called_once()

def test_delete_event_strips_whitespace() -> None:
    """Verifies delete_event correctly strips whitespace from the event ID."""
    service = Mock()
    request_builder = Mock()
    request_builder.delete = AsyncMock(return_value=None)
    service.me.events.by_event_id.return_value = request_builder

    client = OutlookClient(service=service)

    def _fake_run(coro: Coroutine[Any, Any, Any]) -> None:
        coro.close()

    with patch.object(client, "_run", side_effect=_fake_run) as run_mock:
        raw_id = "   test-event-id   "
        client.delete_event(raw_id)

        service.me.events.by_event_id.assert_called_once_with("test-event-id")
        request_builder.delete.assert_called_once_with()
        run_mock.assert_called_once()

@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_outlook_client_delete_event_invalid_id_raises(invalid_id: str) -> None:
    """Verifies delete_event rejects empty/whitespace IDs."""
    client = OutlookClient(service=Mock())

    with pytest.raises(ValueError, match="non-empty string"):
        client.delete_event(invalid_id)

