"""Cross-vertical chat integration tests using the real shared chat API.

The chat integration is verified end-to-end through the real chat router,
real ``Team12SlackClient`` adapter, and the real ``chat_client_api`` registry.
Only the slack-sdk transport layer is faked so the test does not need a live
HTTP server — this keeps the test fast and stable in CI.
"""

from __future__ import annotations

from dataclasses import replace
from http import HTTPStatus
from typing import Any

import pytest
from chat_client_api.client import _ClientRegistry, register_client
from fastapi.testclient import TestClient


class _FakeSlackWebClient:
    """Minimal slack-sdk WebClient stand-in for integration assertions."""

    def __init__(self) -> None:
        """Record outbound calls so the test can assert on them."""
        self.calls: list[dict[str, Any]] = []

    def chat_postMessage(self, *, channel: str, text: str) -> dict[str, Any]:  # noqa: N802
        """Record a chat.postMessage call and return a Slack-like success payload."""
        self.calls.append({"channel": channel, "text": text})
        return {
            "ok": True,
            "channel": channel,
            "ts": "1770000000.000001",
            "bot_id": "B_CALENDAR",
            "message": {"text": text},
        }


@pytest.mark.integration
def test_chat_route_uses_registered_shared_chat_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /chat/ should send the AI response through the registered chat client."""
    from outlook_client_service.config import settings
    from outlook_client_service.routers.chat import get_chat_intelligent_app
    from outlook_client_service.slack_chat_client import Team12SlackClient

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

    fake_web_client = _FakeSlackWebClient()
    register_client(
        lambda: Team12SlackClient(token="xoxb-test", web_client=fake_web_client),
    )

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
    assert fake_web_client.calls == [
        {"channel": "C_INTEGRATION", "text": "Created event: review at 2pm."},
    ]
