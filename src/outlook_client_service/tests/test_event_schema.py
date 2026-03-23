"""Unit tests for event schema validation."""

from datetime import UTC, datetime

import pytest
from outlook_client_service.schemas.event import EventUpdateRequest
from pydantic import ValidationError


class TestEventUpdateRequest:
    """Group tests for EventUpdateRequest validation."""

    def setup_method(self) -> None:
        """Create shared datetime fixtures for each test."""
        self.starts_at = datetime(2026, 3, 20, 9, 0, 0, tzinfo=UTC)
        self.ends_at = datetime(2026, 3, 20, 10, 0, 0, tzinfo=UTC)

    def test_accept_single_field_patch(self) -> None:
        """Accept a patch when one field is provided."""
        request = EventUpdateRequest(title="Updated title")

        assert request.title == "Updated title"
        assert request.starts_at is None
        assert request.ends_at is None
        assert request.location is None
        assert request.description is None

    def test_raise_when_all_fields_are_missing(self) -> None:
        """Raise a validation error when all update fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            EventUpdateRequest()

        assert "At least one field must be provided for update." in str(
            exc_info.value,
        )

    def test_accept_valid_start_and_end_order(self) -> None:
        """Accept a patch when ends_at is later than starts_at."""
        request = EventUpdateRequest(
            starts_at=self.starts_at,
            ends_at=self.ends_at,
        )

        assert request.starts_at == self.starts_at
        assert request.ends_at == self.ends_at

    def test_raise_when_end_is_not_later_than_start(self) -> None:
        """Raise a validation error when ends_at is not later than starts_at."""
        with pytest.raises(ValidationError) as exc_info:
            EventUpdateRequest(
                starts_at=self.starts_at,
                ends_at=self.starts_at,
            )

        assert "ends_at must be later than starts_at." in str(exc_info.value)
