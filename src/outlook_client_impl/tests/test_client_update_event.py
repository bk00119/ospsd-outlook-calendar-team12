"""Contract-style tests for OutlookClient.update_event."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from calendar_client_api import event

from outlook_client_impl.outlook_impl import OutlookClient


@pytest.fixture
def graph_chain() -> dict[str, Any]:
    """Build a minimal Graph builder chain mock.

    update_event uses:
        service.me.events.by_event_id(event_id).patch(body)

    This fixture returns the service plus the intermediate mocks so tests can
    assert calls and configure return values.
    """
    service = MagicMock(name="service")
    me = MagicMock(name="me")
    events = MagicMock(name="events")
    request_builder = MagicMock(name="request_builder")

    service.me = me
    me.events = events
    events.by_event_id.return_value = request_builder

    return {
        "service": service,
        "me": me,
        "events": events,
        "request_builder": request_builder,
    }


@pytest.fixture
def client(graph_chain: dict[str, Any]) -> OutlookClient:
    """Create OutlookClient with an injected service (no auth)."""
    return OutlookClient(service=graph_chain["service"])


class TestUpdateEventValidation:
    """Validation tests for update_event input handling."""

    def test_update_event_raises_value_error_when_event_id_blank(
        self, client: OutlookClient,
    ) -> None:
        """Ensure blank or empty payload inputs raise ValueError."""
        with pytest.raises(ValueError, match="event_id must be a non-empty string"):
            client.update_event("   ", event.EventPatch(title="x"))

    def test_update_event_raises_value_error_when_payload_empty(
        self, client: OutlookClient,
    ) -> None:
        """Ensure blank or empty payload inputs raise ValueError."""
        with pytest.raises(ValueError, match="payload must update at least one field"):
            client.update_event("abc", event.EventPatch())


class TestUpdateEventProviderCalls:
    """Tests covering provider builder-chain interactions."""

    def test_update_event_calls_by_event_id_with_stripped_id(
        self, client: OutlookClient, graph_chain: dict[str, Any],
    ) -> None:
        """Verify correct provider method selection and error handling."""
        rb = graph_chain["request_builder"]
        rb.patch.return_value = None

        # Avoid depending on event parsing; just ensure fallback get_event path is reached.
        client.get_event = MagicMock(return_value=MagicMock())  # type: ignore[method-assign]

        client.update_event("  abc  ", event.EventPatch(title="New"))

        graph_chain["events"].by_event_id.assert_called_once_with("abc")
        rb.patch.assert_called_once()

    def test_update_event_prefers_patch_method_when_available(
        self, client: OutlookClient, graph_chain: dict[str, Any],
    ) -> None:
        """Verify correct provider method selection and error handling."""
        rb = graph_chain["request_builder"]
        rb.patch.return_value = None
        rb.update.return_value = None

        client.get_event = MagicMock(return_value=MagicMock())  # type: ignore[method-assign]

        client.update_event("abc", event.EventPatch(title="New"))

        assert rb.patch.call_count == 1
        assert rb.update.call_count == 0

    def test_update_event_uses_update_when_patch_missing(
        self, client: OutlookClient, graph_chain: dict[str, Any],
    ) -> None:
        """Verify correct provider method selection and error handling."""
        rb = graph_chain["request_builder"]
        del rb.patch  # simulate older SDK surface
        rb.update.return_value = None

        client.get_event = MagicMock(return_value=MagicMock())  # type: ignore[method-assign]

        client.update_event("abc", event.EventPatch(title="New"))

        assert rb.update.call_count == 1

    def test_update_event_raises_not_implemented_when_by_event_id_missing(
        self, graph_chain: dict[str, Any],
    ) -> None:
        """Verify correct provider method selection and error handling."""
        service = graph_chain["service"]
        # Remove by_event_id from the chain
        del service.me.events.by_event_id
        c = OutlookClient(service=service)

        with pytest.raises(NotImplementedError, match="does not support event updates"):
            c.update_event("abc", event.EventPatch(title="New"))

    def test_update_event_raises_not_implemented_when_neither_patch_nor_update_exists(
        self, client: OutlookClient, graph_chain: dict[str, Any],
    ) -> None:
        """Verify correct provider method selection and error handling."""
        rb = graph_chain["request_builder"]
        del rb.patch
        del rb.update

        with pytest.raises(NotImplementedError, match="does not expose patch\\(\\) or update\\(\\)"):
            client.update_event("abc", event.EventPatch(title="New"))


class TestUpdateEventReturnBehavior:
    """Tests for update_event return-value behavior."""

    def test_update_event_returns_event_built_from_patch_payload_when_patch_returns_payload(
        self, client: OutlookClient, graph_chain: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Ensure PATCH payload is preferred and GET fallback works."""
        rb = graph_chain["request_builder"]

        # Patch returns a mapping; OutlookClient will serialize it as JSON string.
        rb.patch.return_value = {"id": "abc", "subject": "New"}

        sentinel = MagicMock(name="event_from_patch")

        def fake_get_event(*, event_id: str, raw_data: str) -> object:
            assert event_id == "abc"
            assert '"id"' in raw_data
            return sentinel

        monkeypatch.setattr(event, "get_event", fake_get_event)

        got = client.update_event("abc", event.EventPatch(title="New"))

        assert got is sentinel

    def test_update_event_falls_back_to_get_event_when_patch_returns_none(
        self, client: OutlookClient, graph_chain: dict[str, Any],
    ) -> None:
        """Ensure PATCH payload is preferred and GET fallback works."""
        rb = graph_chain["request_builder"]
        rb.patch.return_value = None

        sentinel = MagicMock(name="event_from_get")
        client.get_event = MagicMock(return_value=sentinel)  # type: ignore[method-assign]

        got = client.update_event("abc", event.EventPatch(title="New"))

        assert got is sentinel
        client.get_event.assert_called_once_with("abc")


class TestUpdateEventAsyncHandling:
    """Tests ensuring coroutine results are handled correctly."""

    def test_update_event_handles_coroutine_returned_by_patch(
        self, client: OutlookClient, graph_chain: dict[str, Any], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify coroutine returned by patch() is awaited."""
        rb = graph_chain["request_builder"]

        async def patch_coro() -> object:
            return {"id": "abc", "subject": "New"}

        rb.patch.return_value = patch_coro()

        sentinel = MagicMock(name="event_from_patch")

        def fake_get_event(*, event_id: str, raw_data: str) -> object:
            assert event_id == "abc"
            assert '"id"' in raw_data
            return sentinel

        monkeypatch.setattr(event, "get_event", fake_get_event)

        got = client.update_event("abc", event.EventPatch(title="New"))

        assert got is sentinel


class TestUpdateEventPatchModel:
    """Tests for GraphEvent patch model construction."""

    def test_build_patch_event_sets_start_end_as_utc_models(self, client: OutlookClient) -> None:
        """Ensure start/end datetimes are converted to UTC models."""
        starts = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        ends = datetime(2026, 3, 1, 13, 0, 0, tzinfo=UTC)

        patch = event.EventPatch(starts_at=starts, ends_at=ends)
        graph_event = client._build_patch_event(patch)

        assert graph_event.start is not None
        assert graph_event.end is not None
        assert graph_event.start.time_zone == "UTC"
        assert graph_event.end.time_zone == "UTC"

    def test_build_patch_event_sets_body_text_from_description_trimmed(
            self, client: OutlookClient,
    ) -> None:
        """Ensure description maps to plain-text body with trimming."""
        patch = event.EventPatch(description="  hello world  ")
        graph_event = client._build_patch_event(patch)

        assert graph_event.body is not None
        # BodyType.Text in msgraph models is an enum; easiest stable check:
        assert graph_event.body.content_type is not None
        assert graph_event.body.content_type.name == "Text"
        assert graph_event.body.content == "hello world"

    def test_build_patch_event_sets_location_display_name_from_location_trimmed(
            self, client: OutlookClient,
    ) -> None:
        """Ensure location maps to display_name with trimming."""
        patch = event.EventPatch(location="  NYU  ")
        graph_event = client._build_patch_event(patch)

        assert graph_event.location is not None
        assert graph_event.location.display_name == "NYU"
