"""Contract-style test for OutlookClient.create_event."""

from unittest.mock import Mock

from calendar_client_api import event as event_contract

from outlook_client_impl.outlook_impl import OutlookClient


def test_outlook_client_create_event() -> None:
    """Verifies the Outlook client create_event call contract."""
    mock_event = Mock(spec=event_contract.Event)
    mock_client = Mock(spec=OutlookClient)
    mock_client.create_event.return_value = mock_event

    created_event = mock_client.create_event(event_data=mock_event)

    mock_client.create_event.assert_called_once_with(event_data=mock_event)
    assert created_event is mock_event
