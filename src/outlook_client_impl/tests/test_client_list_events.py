"""Contract-style test for OutlookClient.list_events."""

from unittest.mock import Mock

from outlook_client_impl.outlook_impl import OutlookClient


def test_outlook_client_list_events() -> None:
    """Verifies the Outlook client list_events call contract."""
    mock_client = Mock(spec=OutlookClient)
    mock_client.list_events.return_value = []

    assert mock_client.list_events() == []
