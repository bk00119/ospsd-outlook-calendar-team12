"""Tests for the IntelligentAppService AI Orchestration layer."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from intelligent_app_service.service import IntelligentAppService

EXPECTED_TOOL_COUNT = 5


def _make_service(
    mock_ai: MagicMock | None = None,
    mock_calendar: MagicMock | None = None,
) -> tuple[IntelligentAppService, MagicMock, MagicMock]:
    """Create an IntelligentAppService with mock dependencies."""
    ai = mock_ai or MagicMock()
    cal = mock_calendar or MagicMock()
    ai.generate_text.return_value.text = "Done."
    return IntelligentAppService(ai_client=ai, calendar_client=cal), ai, cal


def _extract_tools(mock_ai: MagicMock) -> dict[str, Callable[..., Any]]:
    """Extract the tool functions passed to the AI from the last generate_text call."""
    req_obj = mock_ai.generate_text.call_args.args[0]
    return {t.__name__: t for t in req_obj.tools}


# ── Context & Wiring Tests ──────────────────────────────────────────────


@pytest.mark.unit
def test_process_chat_injects_timezone_context() -> None:
    """Verify timezone, conflict rule, and user message are injected correctly."""
    service, mock_ai, _ = _make_service()

    response = service.process_chat(
        message="Schedule lunch tomorrow at noon",
        user_timezone="America/New_York",
    )

    assert response == "Done."
    mock_ai.generate_text.assert_called_once()

    req_obj = mock_ai.generate_text.call_args.args[0]
    assert "America/New_York" in req_obj.context.get("system_instructions", "")
    assert "CRITICAL CONFLICT RULE" in req_obj.context.get("system_instructions", "")
    assert "Schedule lunch tomorrow at noon" in req_obj.prompt
    assert len(req_obj.tools) == EXPECTED_TOOL_COUNT
    assert req_obj.tools[0].__name__ == "create_outlook_event"


@pytest.mark.unit
def test_process_chat_defaults_to_utc() -> None:
    """Verify default timezone is UTC when not specified."""
    service, mock_ai, _ = _make_service()
    service.process_chat(message="What's on my calendar?")

    req_obj = mock_ai.generate_text.call_args.args[0]
    assert "UTC" in req_obj.context.get("system_instructions", "")


# ── Tool Execution Tests ────────────────────────────────────────────────


@pytest.mark.unit
def test_tool_create_event_calls_calendar() -> None:
    """Verify create_outlook_event tool delegates to calendar client."""
    service, mock_ai, mock_cal = _make_service()

    mock_event = MagicMock()
    mock_event.id = "evt-created-1"
    mock_cal.list_events.return_value = []
    mock_cal.create_event.return_value = mock_event

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["create_outlook_event"](
        title="Team Sync",
        start_iso_string="2026-04-23T14:00:00+00:00",
        end_iso_string="2026-04-23T15:00:00+00:00",
    )

    mock_cal.create_event.assert_called_once()
    assert "evt-created-1" in result


@pytest.mark.unit
def test_tool_create_event_rejects_time_conflict() -> None:
    """Verify create_outlook_event refuses to create conflicting events."""
    service, mock_ai, mock_cal = _make_service()
    existing_event = MagicMock()
    mock_cal.list_events.return_value = [existing_event]

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["create_outlook_event"](
        title="Team Sync",
        start_iso_string="2026-04-23T14:00:00+00:00",
        end_iso_string="2026-04-23T15:00:00+00:00",
    )

    mock_cal.create_event.assert_not_called()
    assert "conflicts" in result


@pytest.mark.unit
def test_tool_list_events_returns_formatted_string() -> None:
    """Verify list_my_events formats event data correctly."""
    service, mock_ai, mock_cal = _make_service()

    fake_event = MagicMock()
    fake_event.title = "Standup"
    fake_event.id = "evt-1"
    fake_event.starts_at = datetime(2026, 4, 23, 9, 0, tzinfo=UTC)
    fake_event.ends_at = datetime(2026, 4, 23, 9, 30, tzinfo=UTC)
    fake_event.location = "Room 42"
    fake_event.description = "Daily sync"
    mock_cal.list_events.return_value = [fake_event]

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["list_my_events"](
        start_iso_string="2026-04-23T00:00:00+00:00",
        end_iso_string="2026-04-23T23:59:59+00:00",
    )

    assert "Standup" in result
    assert "evt-1" in result
    assert "Room 42" in result
    assert "Daily sync" in result


@pytest.mark.unit
def test_tool_list_events_empty_calendar() -> None:
    """Verify list_my_events returns free message when no events exist."""
    service, mock_ai, mock_cal = _make_service()
    mock_cal.list_events.return_value = []

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["list_my_events"](
        start_iso_string="2026-04-23T00:00:00+00:00",
        end_iso_string="2026-04-23T23:59:59+00:00",
    )

    assert "free" in result.lower()


@pytest.mark.unit
def test_tool_delete_event_calls_calendar() -> None:
    """Verify delete_outlook_event delegates to calendar client."""
    service, mock_ai, mock_cal = _make_service()

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["delete_outlook_event"](event_id="evt-delete-me")

    mock_cal.delete_event.assert_called_once_with("evt-delete-me")
    assert "evt-delete-me" in result


@pytest.mark.unit
def test_tool_get_event_returns_details() -> None:
    """Verify get_outlook_event returns formatted event details."""
    service, mock_ai, mock_cal = _make_service()

    fake_event = MagicMock()
    fake_event.id = "evt-get-1"
    fake_event.title = "Lunch"
    fake_event.starts_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    fake_event.ends_at = datetime(2026, 4, 23, 13, 0, tzinfo=UTC)
    fake_event.location = "Cafe"
    fake_event.description = "Team lunch"
    mock_cal.get_event.return_value = fake_event

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["get_outlook_event"](event_id="evt-get-1")

    assert "Lunch" in result
    assert "evt-get-1" in result
    assert "Cafe" in result
    assert "Team lunch" in result


@pytest.mark.unit
def test_tool_get_event_handles_not_found() -> None:
    """Verify get_outlook_event returns error message when event not found."""
    service, mock_ai, mock_cal = _make_service()
    mock_cal.get_event.side_effect = LookupError("Event not found")

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["get_outlook_event"](event_id="nonexistent")

    assert "Error" in result


@pytest.mark.unit
def test_tool_update_event_calls_calendar() -> None:
    """Verify update_outlook_event delegates to calendar client with correct patch."""
    service, mock_ai, mock_cal = _make_service()

    mock_event = MagicMock()
    mock_event.id = "evt-updated-1"
    mock_cal.update_event.return_value = mock_event

    service.process_chat(message="test")
    tools = _extract_tools(mock_ai)

    result = tools["update_outlook_event"](
        event_id="evt-updated-1",
        new_title="Renamed Meeting",
        new_location="Conference Room B",
        new_description="Updated agenda",
    )

    mock_cal.update_event.assert_called_once()
    patch_arg = mock_cal.update_event.call_args.args[1]
    assert patch_arg.title == "Renamed Meeting"
    assert patch_arg.location == "Conference Room B"
    assert patch_arg.description == "Updated agenda"
    assert "evt-updated-1" in result
