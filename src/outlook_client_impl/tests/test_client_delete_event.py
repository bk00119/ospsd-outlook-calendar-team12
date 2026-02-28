"""Contract-style test for OutlookClient.delete_event."""
from unittest.mock import Mock

import pytest

from outlook_client_impl.outlook_impl import OutlookClient


def test_outlook_client_delete_event_success() -> None:
    """Verifies the Outlook client delete_event call contract for successful deletion."""
    mock_service = Mock()
    mock_client = OutlookClient()
    # TODO: Remove ignore after implementing the service integration and properly typing the service attribute
    mock_client.service = mock_service # type: ignore[attr-defined]

    event_id = "test-event-id"
    mock_client.delete_event(event_id=event_id)

    mock_service.delete_event.assert_called_once_with(event_id)

@pytest.mark.parametrize("invalid_id", ["", "   "])
def test_outlook_client_delete_event_invalid_id_raises(invalid_id: str) -> None:
    """Verifies the Outlook client delete_event call contract for invalid event_id."""
    client = OutlookClient()

    with pytest.raises(ValueError, match="non-empty string"):
        client.delete_event(invalid_id)

def test_outlook_client_delete_event_no_service_raises() -> None:
    """Verifies the Outlook client delete_event call contract for missing service instance."""
    client = OutlookClient()

    with pytest.raises(RuntimeError, match="not configured with a service instance"):
        client.delete_event(event_id="test-event-id")

def test_outlook_client_delete_event_service_no_delete_method_raises() -> None:
    """Verifies the Outlook client delete_event call contract for service instance missing delete method."""

    class NoDeleteService:
        pass

    mock_client = OutlookClient()
    # TODO: Remove ignore after implementing the service integration and properly typing the service attribute
    mock_client.service = NoDeleteService() # type: ignore[attr-defined]

    with pytest.raises(NotImplementedError, match="delete_event method"):
        mock_client.delete_event("test-event-id")
