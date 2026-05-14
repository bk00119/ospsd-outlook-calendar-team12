"""Cross-vertical chat integration tests using the real shared chat API."""

from __future__ import annotations

import json
from dataclasses import replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from typing import Any, ClassVar
from urllib.parse import parse_qs

import pytest
from chat_client_api.client import _ClientRegistry, register_client
from fastapi.testclient import TestClient
from slack_sdk import WebClient


class _SlackStubHandler(BaseHTTPRequestHandler):
    """HTTP handler that records Slack-style send-message requests."""

    recorded_requests: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        """Record a POST request and return a Slack-like JSON response."""
        body_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(body_length)
        body_text = body.decode("utf-8")
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            payload = {
                key: values[0]
                for key, values in parse_qs(body_text).items()
            }
        self.recorded_requests.append({"path": self.path, "json": payload})

        response = {
            "ok": True,
            "channel": payload["channel"],
            "ts": "1770000000.000001",
            "bot_id": "B_CALENDAR",
            "message": {"text": payload["text"]},
        }
        response_body = json.dumps(response).encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Silence default HTTP server logging during tests."""


class _SlackStubServer(ThreadingHTTPServer):
    """Threaded HTTP stub that does not block process exit in CI."""

    daemon_threads = True
    allow_reuse_address = True


@pytest.mark.integration
def test_chat_route_uses_registered_shared_chat_client_against_http_stub(
    free_tcp_port: int,
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
    for proxy_env in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(proxy_env, raising=False)
    _SlackStubHandler.recorded_requests = []
    server = _SlackStubServer(("127.0.0.1", free_tcp_port), _SlackStubHandler)
    server_ready = Event()

    def serve_stub() -> None:
        server_ready.set()
        server.serve_forever(poll_interval=0.05)

    server_thread = Thread(
        target=serve_stub,
        name="slack-stub-http-server",
        daemon=True,
    )
    server_thread.start()
    assert server_ready.wait(timeout=2)
    register_client(
        lambda: Team12SlackClient(
            token="xoxb-test",
            web_client=WebClient(
                token="xoxb-test",
                base_url=f"http://127.0.0.1:{free_tcp_port}/",
                timeout=2,
            ),
        ),
    )

    app = main.create_app()
    stub_service = StubService()
    app.dependency_overrides[get_chat_intelligent_app] = lambda: stub_service

    try:
        response = TestClient(app).post(
            "/chat/",
            json={
                "message": "Schedule the review at 2pm",
                "channel_id": "C_INTEGRATION",
                "timezone": "America/New_York",
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"response": "Created event: review at 2pm."}
    assert _SlackStubHandler.recorded_requests == [
        {
            "path": "/chat.postMessage",
            "json": {"channel": "C_INTEGRATION", "text": "Created event: review at 2pm."},
        },
    ]
