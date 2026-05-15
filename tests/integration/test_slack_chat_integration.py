"""Cross-vertical chat integration tests using the real shared chat API."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import pytest
from calendar_client_api.event import Event, EventPatch
from chat_client_api.client import _ClientRegistry, register_client
from fastapi.testclient import TestClient
from intelligent_app_service.service import IntelligentAppService
from slack_sdk import WebClient
from werkzeug import Response

from ai_client_api import (
    AIClient,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TextGenerationRequest,
    TextGenerationResponse,
)
from calendar_client_api import Client as CalendarClient

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer
    from werkzeug.wrappers import Request


@dataclass(frozen=True)
class _StubEvent(Event):
    """Concrete event used by the integration test calendar stub."""

    event_id: str
    event_title: str
    event_starts_at: datetime
    event_ends_at: datetime
    event_location: str | None = None
    event_description: str | None = None

    @property
    def id(self) -> str:
        """Return the event ID."""
        return self.event_id

    @property
    def title(self) -> str:
        """Return the event title."""
        return self.event_title

    @property
    def starts_at(self) -> datetime:
        """Return the event start time."""
        return self.event_starts_at

    @property
    def ends_at(self) -> datetime:
        """Return the event end time."""
        return self.event_ends_at

    @property
    def location(self) -> str | None:
        """Return the event location."""
        return self.event_location

    @property
    def description(self) -> str | None:
        """Return the event description."""
        return self.event_description


class _ToolCallingAI(AIClient):
    """AI stub that exercises the real intelligent-app tool-calling path."""

    def generate_text(self, request: TextGenerationRequest) -> TextGenerationResponse:
        """Invoke the create-event tool exposed by IntelligentAppService."""
        assert request.prompt == "Schedule the review at 2pm"
        assert "America/New_York" in str(request.context)
        assert request.tools is not None

        tools = {tool.__name__: tool for tool in request.tools}
        result = tools["create_outlook_event"](
            title="Review",
            start_iso_string="2026-05-14T14:00:00+00:00",
            end_iso_string="2026-05-14T15:00:00+00:00",
            location="Zoom",
            description="Project review",
        )
        return TextGenerationResponse(text=result)

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Structured generation is not used by this integration path."""
        raise NotImplementedError


class _RecordingCalendar(CalendarClient):
    """Calendar stub that records real domain actions performed by the AI tool."""

    def __init__(self) -> None:
        """Initialize an empty in-memory calendar."""
        self.created_events: list[_StubEvent] = []
        self.list_windows: list[tuple[datetime | None, datetime | None]] = []

    def get_event(self, event_id: str) -> Event:
        """Return an existing event by ID."""
        for event in self.created_events:
            if event.id == event_id:
                return event
        raise LookupError(event_id)

    def list_events(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        types: list[str] | None = None,
    ) -> list[Event]:
        """Record the conflict-check window and return no conflicts."""
        del types
        self.list_windows.append((start, end))
        return []

    def create_event(
        self,
        title: str,
        starts_at: datetime,
        ends_at: datetime,
        location: str | None = None,
        description: str | None = None,
    ) -> Event:
        """Create and store an event."""
        event = _StubEvent(
            event_id="evt-review",
            event_title=title,
            event_starts_at=starts_at,
            event_ends_at=ends_at,
            event_location=location,
            event_description=description,
        )
        self.created_events.append(event)
        return event

    def delete_event(self, event_id: str) -> None:
        """Delete is outside this integration path."""
        raise NotImplementedError

    def update_event(self, event_id: str, payload: EventPatch) -> Event:
        """Update is outside this integration path."""
        raise NotImplementedError


def _clear_proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent Slack SDK calls to the local stub from using proxy settings."""
    for proxy_env in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(proxy_env, raising=False)


def _register_slack_http_stub(
    httpserver: HTTPServer,
) -> list[dict[str, Any]]:
    """Register the shared chat client against a pytest-httpserver Slack stub."""
    from outlook_client_service.slack_chat_client import Team12SlackClient

    recorded_requests: list[dict[str, Any]] = []

    def handle_slack_post(request: Request) -> Response:
        body_text = request.get_data(as_text=True)
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            payload = {key: values[0] for key, values in parse_qs(body_text).items()}
        recorded_requests.append({"path": request.path, "json": payload})

        response = {
            "ok": True,
            "channel": payload["channel"],
            "ts": "1770000000.000001",
            "bot_id": "B_CALENDAR",
            "message": {"text": payload["text"]},
        }
        return Response(
            json.dumps(response),
            status=HTTPStatus.OK,
            content_type="application/json",
        )

    httpserver.expect_request(
        "/chat.postMessage",
        method="POST",
    ).respond_with_handler(handle_slack_post)

    register_client(
        lambda: Team12SlackClient(
            token="xoxb-test",
            web_client=WebClient(
                token="xoxb-test",
                base_url=f"{httpserver.url_for('/')}",
                timeout=2,
            ),
        ),
    )
    return recorded_requests


@pytest.mark.integration
def test_chat_route_uses_registered_shared_chat_client(
    monkeypatch: pytest.MonkeyPatch,
    httpserver: HTTPServer,
) -> None:
    """POST /chat/ should send the AI response through the Slack SDK HTTP path."""
    from outlook_client_service.config import settings
    from outlook_client_service.routers.chat import get_chat_intelligent_app

    from outlook_client_service import main

    class StubService:
        """Minimal intelligent app stub for the route boundary."""

        def process_chat(self, message: str, user_timezone: str = "UTC") -> str:
            """Return a deterministic AI response."""
            assert message == "Schedule the review at 2pm"
            assert user_timezone == "America/New_York"
            return "Created event: review at 2pm."

    monkeypatch.setattr(_ClientRegistry, "_factory", _ClientRegistry.get())
    monkeypatch.setattr(
        main,
        "settings",
        replace(settings, enable_slack_poller=False),
    )
    _clear_proxy_env(monkeypatch)
    recorded_requests = _register_slack_http_stub(httpserver)

    app = main.create_app()
    stub_service = StubService()
    app.dependency_overrides[get_chat_intelligent_app] = lambda: stub_service

    response = TestClient(app).post(
        "/chat/",
        json={
            "message": "Schedule the review at 2pm",
            "channel_id": "C_INTEGRATION",
            "timezone": "America/New_York",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"response": "Created event: review at 2pm."}
    assert recorded_requests == [
        {
            "path": "/chat.postMessage",
            "json": {
                "channel": "C_INTEGRATION",
                "text": "Created event: review at 2pm.",
                "unfurl_links": False,
                "unfurl_media": False,
            },
        },
    ]


@pytest.mark.integration
def test_chat_request_runs_ai_calendar_action_and_sends_chat_response(
    monkeypatch: pytest.MonkeyPatch,
    httpserver: HTTPServer,
) -> None:
    """POST /chat/ should execute an AI calendar tool and send the result to chat."""
    from outlook_client_service.config import settings
    from outlook_client_service.routers.chat import get_chat_intelligent_app

    from outlook_client_service import main

    monkeypatch.setattr(_ClientRegistry, "_factory", _ClientRegistry.get())
    monkeypatch.setattr(
        main,
        "settings",
        replace(settings, enable_slack_poller=False),
    )
    _clear_proxy_env(monkeypatch)
    recorded_requests = _register_slack_http_stub(httpserver)

    calendar = _RecordingCalendar()
    service = IntelligentAppService(calendar_client=calendar, ai_client=_ToolCallingAI())
    app = main.create_app()
    app.dependency_overrides[get_chat_intelligent_app] = lambda: service

    response = TestClient(app).post(
        "/chat/",
        json={
            "message": "Schedule the review at 2pm",
            "channel_id": "C_INTEGRATION",
            "timezone": "America/New_York",
        },
    )

    expected_start = datetime(2026, 5, 14, 14, tzinfo=UTC)
    expected_end = datetime(2026, 5, 14, 15, tzinfo=UTC)

    assert response.status_code == HTTPStatus.OK
    assert calendar.list_windows == [(expected_start, expected_end)]
    assert calendar.created_events == [
        _StubEvent(
            event_id="evt-review",
            event_title="Review",
            event_starts_at=expected_start,
            event_ends_at=expected_end,
            event_location="Zoom",
            event_description="Project review",
        ),
    ]
    response_text = response.json()["response"]
    assert response_text.startswith("Created event 'Review' (ID: evt-review)")
    assert recorded_requests == [
        {
            "path": "/chat.postMessage",
            "json": {
                "channel": "C_INTEGRATION",
                "text": response_text,
                "unfurl_links": False,
                "unfurl_media": False,
            },
        },
    ]
