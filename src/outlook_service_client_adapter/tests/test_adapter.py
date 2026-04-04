"""Tests for the ServiceClientAdapter."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from calendar_client_api.event import EventPatch
from outlook_client_service_api_client.models.event_response import EventResponse
from outlook_client_service_api_client.models.http_validation_error import HTTPValidationError
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


class TestGetEvent:
    """Tests for the get_event adapter method."""

    def setup_method(self) -> None:
        """Create a mock generated client and shared event data for each test."""
        self.generated_client = MagicMock()
        self.adapter = ServiceClientAdapter(self.generated_client)
        self.event_id = "event-123"
        self.starts_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 25, 10, 0, tzinfo=UTC)

    @patch("outlook_service_client_adapter.adapter.get_event_events_event_id_get")
    def test_delegates_to_generated_client(self, mock_get: MagicMock) -> None:
        """Call generated get function with the expected event ID."""
        mock_get.sync.return_value = EventResponse(
            id=self.event_id,
            title="Team sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room A",
            description="Discuss roadmap",
        )

        self.adapter.get_event(self.event_id)

        mock_get.sync.assert_called_once_with(
            event_id=self.event_id,
            client=self.generated_client,
        )

    @patch("outlook_service_client_adapter.adapter.get_event_events_event_id_get")
    def test_maps_event_response_to_event_contract(self, mock_get: MagicMock) -> None:
        """Return an Event-compatible object mapped from generated EventResponse."""
        mock_get.sync.return_value = EventResponse(
            id=self.event_id,
            title="Team sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location=None,
            description=None,
        )

        event = self.adapter.get_event(self.event_id)

        assert event.id == self.event_id
        assert event.title == "Team sync"
        assert event.starts_at == self.starts_at
        assert event.ends_at == self.ends_at
        assert event.location is None
        assert event.description is None

    @patch("outlook_service_client_adapter.adapter.get_event_events_event_id_get")
    def test_raises_runtime_error_on_empty_response(self, mock_get: MagicMock) -> None:
        """Raise RuntimeError when generated get returns no payload."""
        mock_get.sync.return_value = None

        with pytest.raises(RuntimeError, match="get_event returned no response payload"):
            self.adapter.get_event(self.event_id)

    @patch("outlook_service_client_adapter.adapter.get_event_events_event_id_get")
    def test_raises_type_error_on_validation_response(self, mock_get: MagicMock) -> None:
        """Raise TypeError when service returns validation error payload."""
        mock_get.sync.return_value = HTTPValidationError()

        with pytest.raises(TypeError, match="get_event validation failed"):
            self.adapter.get_event(self.event_id)

    @patch("outlook_service_client_adapter.adapter.get_event_events_event_id_get")
    def test_propagates_generated_client_exception(self, mock_get: MagicMock) -> None:
        """Propagate exceptions from generated get call."""
        mock_get.sync.side_effect = Exception("network failure")

        with pytest.raises(Exception, match="network failure"):
            self.adapter.get_event(self.event_id)


class TestCreateEvent:
    """Tests for the create_event adapter method."""

    def setup_method(self) -> None:
        """Create a mock generated client for each test."""
        self.generated_client = MagicMock()
        self.adapter = ServiceClientAdapter(self.generated_client)
        self.starts_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 25, 10, 0, tzinfo=UTC)

    @patch("outlook_service_client_adapter.adapter.create_event_events_post")
    def test_delegates_to_generated_client_with_expected_body(self, mock_create: MagicMock) -> None:
        """Call generated create function with mapped EventCreateRequest payload."""
        mock_create.sync.return_value = EventResponse(
            id="evt-1",
            title="Team sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room A",
            description="Discuss roadmap",
        )

        self.adapter.create_event(
            title="Team sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room A",
            description="Discuss roadmap",
        )

        mock_create.sync.assert_called_once()
        call_kwargs = mock_create.sync.call_args.kwargs
        assert call_kwargs["client"] is self.generated_client
        body = call_kwargs["body"]
        assert body.title == "Team sync"
        assert body.starts_at == self.starts_at
        assert body.ends_at == self.ends_at
        assert body.location == "Room A"
        assert body.description == "Discuss roadmap"

    @patch("outlook_service_client_adapter.adapter.create_event_events_post")
    def test_maps_event_response_to_event_contract(self, mock_create: MagicMock) -> None:
        """Return an Event-compatible object mapped from generated EventResponse."""
        mock_create.sync.return_value = EventResponse(
            id="evt-2",
            title="1:1",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location=None,
            description=None,
        )

        event = self.adapter.create_event(
            title="1:1",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
        )

        assert event.id == "evt-2"
        assert event.title == "1:1"
        assert event.starts_at == self.starts_at
        assert event.ends_at == self.ends_at
        assert event.location is None
        assert event.description is None

    @patch("outlook_service_client_adapter.adapter.create_event_events_post")
    def test_raises_runtime_error_on_empty_response(self, mock_create: MagicMock) -> None:
        """Raise RuntimeError when generated create returns no payload."""
        mock_create.sync.return_value = None

        with pytest.raises(RuntimeError, match="create_event returned no response payload"):
            self.adapter.create_event(
                title="Empty",
                starts_at=self.starts_at,
                ends_at=self.ends_at,
            )

    @patch("outlook_service_client_adapter.adapter.create_event_events_post")
    def test_raises_type_error_on_validation_response(self, mock_create: MagicMock) -> None:
        """Raise TypeError when service returns validation error payload."""
        mock_create.sync.return_value = HTTPValidationError()

        with pytest.raises(TypeError, match="create_event validation failed"):
            self.adapter.create_event(
                title="Bad",
                starts_at=self.starts_at,
                ends_at=self.ends_at,
            )

    @patch("outlook_service_client_adapter.adapter.create_event_events_post")
    def test_propagates_generated_client_exception(self, mock_create: MagicMock) -> None:
        """Propagate exceptions from generated create call."""
        mock_create.sync.side_effect = Exception("network failure")

        with pytest.raises(Exception, match="network failure"):
            self.adapter.create_event(
                title="Err",
                starts_at=self.starts_at,
                ends_at=self.ends_at,
            )


class TestUpdateEvent:
    """Tests for the update_event adapter method."""

    def setup_method(self) -> None:
        """Create a mock generated client and shared event data for each test."""
        self.generated_client = MagicMock()
        self.adapter = ServiceClientAdapter(self.generated_client)
        self.event_id = "event-456"
        self.starts_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 25, 10, 0, tzinfo=UTC)
        self.payload = EventPatch(
            title="Updated sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room B",
            description="Updated agenda",
        )

    @patch("outlook_service_client_adapter.adapter.update_event_events_event_id_patch")
    def test_delegates_to_generated_client_with_expected_body(
        self,
        mock_update: MagicMock,
    ) -> None:
        """Call generated update function with mapped EventUpdateRequest payload."""
        mock_update.sync.return_value = EventResponse(
            id=self.event_id,
            title="Updated sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location="Room B",
            description="Updated agenda",
        )

        self.adapter.update_event(self.event_id, self.payload)

        mock_update.sync.assert_called_once()
        call_kwargs = mock_update.sync.call_args.kwargs
        assert call_kwargs["client"] is self.generated_client
        assert call_kwargs["event_id"] == self.event_id
        body = call_kwargs["body"]
        assert body.title == "Updated sync"
        assert body.starts_at == self.starts_at
        assert body.ends_at == self.ends_at
        assert body.location == "Room B"
        assert body.description == "Updated agenda"

    @patch("outlook_service_client_adapter.adapter.update_event_events_event_id_patch")
    def test_maps_event_response_to_event_contract(
        self,
        mock_update: MagicMock,
    ) -> None:
        """Return an Event-compatible object mapped from generated EventResponse."""
        mock_update.sync.return_value = EventResponse(
            id=self.event_id,
            title="Updated sync",
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            location=None,
            description=None,
        )

        event = self.adapter.update_event(self.event_id, self.payload)

        assert event.id == self.event_id
        assert event.title == "Updated sync"
        assert event.starts_at == self.starts_at
        assert event.ends_at == self.ends_at
        assert event.location is None
        assert event.description is None

    @patch("outlook_service_client_adapter.adapter.update_event_events_event_id_patch")
    def test_raises_runtime_error_on_empty_response(
        self,
        mock_update: MagicMock,
    ) -> None:
        """Raise RuntimeError when generated update returns no payload."""
        mock_update.sync.return_value = None

        with pytest.raises(RuntimeError, match="update_event returned no response payload"):
            self.adapter.update_event(self.event_id, self.payload)

    @patch("outlook_service_client_adapter.adapter.update_event_events_event_id_patch")
    def test_raises_type_error_on_validation_response(
        self,
        mock_update: MagicMock,
    ) -> None:
        """Raise TypeError when service returns validation error payload."""
        mock_update.sync.return_value = HTTPValidationError()

        with pytest.raises(TypeError, match="update_event validation failed"):
            self.adapter.update_event(self.event_id, self.payload)

    @patch("outlook_service_client_adapter.adapter.update_event_events_event_id_patch")
    def test_propagates_generated_client_exception(
        self,
        mock_update: MagicMock,
    ) -> None:
        """Propagate exceptions from generated update call."""
        mock_update.sync.side_effect = Exception("network failure")

        with pytest.raises(Exception, match="network failure"):
            self.adapter.update_event(self.event_id, self.payload)


class TestListEvents:
    """Tests for the list_events adapter method."""

    def setup_method(self) -> None:
        """Create a mock generated client and shared event data for each test."""
        self.generated_client = MagicMock()
        self.adapter = ServiceClientAdapter(self.generated_client)
        self.starts_at = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 25, 10, 0, tzinfo=UTC)

    @patch("outlook_service_client_adapter.adapter.list_events_events_get")
    def test_delegates_to_generated_client(self, mock_list: MagicMock) -> None:
        """Call generated list function with start and end filters."""
        mock_list.sync.return_value = [
            EventResponse(
                id="evt-1",
                title="Team sync",
                starts_at=self.starts_at,
                ends_at=self.ends_at,
                location=None,
                description=None,
            ),
        ]

        self.adapter.list_events(start=self.starts_at, end=self.ends_at)

        mock_list.sync.assert_called_once_with(
            client=self.generated_client,
            start=self.starts_at,
            end=self.ends_at,
        )

    @patch("outlook_service_client_adapter.adapter.list_events_events_get")
    def test_maps_event_responses_to_event_contract(self, mock_list: MagicMock) -> None:
        """Return a list of Event-compatible objects mapped from generated EventResponse."""
        mock_list.sync.return_value = [
            EventResponse(
                id="evt-1",
                title="Team sync",
                starts_at=self.starts_at,
                ends_at=self.ends_at,
                location=None,
                description=None,
            ),
        ]

        events = self.adapter.list_events()

        assert len(events) == 1
        assert events[0].id == "evt-1"
        assert events[0].title == "Team sync"
        assert events[0].starts_at == self.starts_at
        assert events[0].ends_at == self.ends_at

    @patch("outlook_service_client_adapter.adapter.list_events_events_get")
    def test_returns_empty_list_on_none_response(self, mock_list: MagicMock) -> None:
        """Return an empty list when generated client returns None."""
        mock_list.sync.return_value = None

        result = self.adapter.list_events()

        assert result == []

    @patch("outlook_service_client_adapter.adapter.list_events_events_get")
    def test_raises_type_error_on_validation_response(self, mock_list: MagicMock) -> None:
        """Raise TypeError when service returns validation error payload."""
        mock_list.sync.return_value = HTTPValidationError()

        with pytest.raises(TypeError, match="list_events validation failed"):
            self.adapter.list_events()

    @patch("outlook_service_client_adapter.adapter.list_events_events_get")
    def test_propagates_generated_client_exception(self, mock_list: MagicMock) -> None:
        """Propagate exceptions from generated list call."""
        mock_list.sync.side_effect = Exception("network failure")

        with pytest.raises(Exception, match="network failure"):
            self.adapter.list_events()
