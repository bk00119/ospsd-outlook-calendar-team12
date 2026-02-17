"""Contract-style test for OutlookClient.create_event."""

from unittest.mock import Mock

from calendar_client_api import event as event_contract

from outlook_client_impl.outlook_impl import OutlookClient


def test_outlook_client_update_event() -> None:
    """Verifies the Outlook client create_event call contract."""
    mock_event = Mock(spec=event_contract.Event)
    mock_event.id = "event-123"
    mock_event.title = "second meeting"

    mock_patch = Mock(spec=event_contract.EventPatch)
    mock_patch.title = "second meeting"

    mock_client = Mock(spec=OutlookClient)
    mock_client.update_event.return_value = mock_event

    updated_event = mock_client.update_event(event_id="event-123", payload=mock_patch)

    mock_client.update_event.assert_called_once_with(event_id="event-123", payload=mock_patch)
    assert updated_event.title == "second meeting"
