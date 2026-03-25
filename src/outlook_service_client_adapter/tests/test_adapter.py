"""Tests for the ServiceClientAdapter."""

from unittest.mock import MagicMock, patch

import pytest
from outlook_service_client_adapter.adapter import ServiceClientAdapter


class TestDeleteEvent:
    """Tests for the delete_event adapter method."""

    def setup_method(self) -> None:
        """Create a mock generated client for each test."""
        self.generated_client = MagicMock()
        self.adapter = ServiceClientAdapter(self.generated_client)
        self.event_id = "event-123"

    @patch("outlook_service_client_adapter.adapter.delete_event_events_event_id_delete")
    def test_delegates_to_generated_client(self, mock_delete: MagicMock) -> None:
        """Call the generated delete function with correct args."""
        self.adapter.delete_event(self.event_id)

        mock_delete.sync.assert_called_once_with(
            event_id=self.event_id,
            client=self.generated_client,
        )

    @patch("outlook_service_client_adapter.adapter.delete_event_events_event_id_delete")
    def test_propagates_exception(self, mock_delete: MagicMock) -> None:
        """Propagate exceptions from the generated client."""
        mock_delete.sync.side_effect = Exception("connection failed")

        with pytest.raises(Exception, match="connection failed"):
            self.adapter.delete_event(self.event_id)
