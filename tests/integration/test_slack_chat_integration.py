"""Cross-vertical chat integration tests using the real shared chat API."""

from __future__ import annotations

import json
from dataclasses import replace
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import pytest
from chat_client_api.client import _ClientRegistry, register_client
from fastapi.testclient import TestClient
from slack_sdk import WebClient
from werkzeug import Response

if TYPE_CHECKING:
    from pytest_httpserver import HTTPServer
    from werkzeug.wrappers import Request


@pytest.mark.integration
def test_chat_route_uses_registered_shared_chat_client(
    monkeypatch: pytest.MonkeyPatch,
    httpserver: HTTPServer,
) -> None:
    """POST /chat/ should send the AI response through the Slack SDK HTTP path."""
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
    for proxy_env in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(proxy_env, raising=False)

    recorded_requests: list[dict[str, Any]] = []

    def handle_slack_post(request: Request) -> Response:
        body_text = request.get_data(as_text=True)
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            payload = {
                key: values[0]
                for key, values in parse_qs(body_text).items()
            }
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
            "json": {"channel": "C_INTEGRATION", "text": "Created event: review at 2pm."},
        },
    ]
