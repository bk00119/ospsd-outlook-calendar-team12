"""Cross-vertical chat integration tests using the real shared chat API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any, ClassVar

import pytest
import requests
from chat_client_api.client import Channel, ChatClient, Message, _ClientRegistry, register_client
from fastapi.testclient import TestClient


class HttpBackedChatClient(ChatClient):
    """Small HTTP-backed client used to exercise the real shared ChatClient contract."""

    def __init__(self, base_url: str) -> None:
        """Initialize the test client with a stub server URL."""
        self._base_url = base_url.rstrip("/")

    def send_message(self, channel_id: str, text: str) -> Message:
        """Send a message through the HTTP stub."""
        response = requests.post(
            f"{self._base_url}/chat.postMessage",
            json={"channel": channel_id, "text": text},
            timeout=5,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return Message(
            message_id=str(payload["ts"]),
            channel=str(payload["channel"]),
            text=str(payload["message"]["text"]),
            sender=str(payload.get("bot_id", "bot")),
            timestamp=datetime.fromtimestamp(float(payload["ts"]), tz=UTC),
        )

    def get_channels(self) -> list[Channel]:
        """List channels; not needed for this integration path."""
        raise NotImplementedError

    def get_channel(self, channel_id: str) -> Channel:
        """Get one channel; not needed for this integration path."""
        raise NotImplementedError

    def get_messages(
        self,
        channel_id: str,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Message]:
        """Fetch recent messages; not needed for this integration path."""
        raise NotImplementedError

    def get_message(self, message_id: str) -> Message:
        """Fetch one message; not needed for this integration path."""
        raise NotImplementedError

    def delete_message(self, message_id: str) -> None:
        """Delete one message; not needed for this integration path."""
        raise NotImplementedError


class _SlackStubHandler(BaseHTTPRequestHandler):
    """HTTP handler that records Slack-style send-message requests."""

    recorded_requests: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        """Record a POST request and return a Slack-like JSON response."""
        body_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(body_length)
        payload = json.loads(body.decode("utf-8"))
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


@pytest.mark.integration
def test_chat_route_uses_registered_shared_chat_client_against_http_stub(
    free_tcp_port: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /chat/ should send the AI response through the registered chat client."""
    from outlook_client_service.main import create_app
    from outlook_client_service.routers.chat import get_chat_intelligent_app

    class StubService:
        """Minimal intelligent app stub for the route boundary."""

        def process_chat(self, message: str, user_timezone: str = "UTC") -> str:
            """Return a deterministic AI response."""
            assert message == "Schedule the review at 2pm"
            assert user_timezone == "America/New_York"
            return "Created event: review at 2pm."

    monkeypatch.setattr(_ClientRegistry, "_factory", _ClientRegistry.get())
    _SlackStubHandler.recorded_requests = []
    server = ThreadingHTTPServer(("127.0.0.1", free_tcp_port), _SlackStubHandler)
    server_thread = Thread(
        target=server.serve_forever,
        name="slack-stub-http-server",
        daemon=True,
    )
    server_thread.start()
    register_client(lambda: HttpBackedChatClient(f"http://127.0.0.1:{free_tcp_port}"))

    app = create_app()
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

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"response": "Created event: review at 2pm."}
    assert _SlackStubHandler.recorded_requests == [
        {
            "path": "/chat.postMessage",
            "json": {"channel": "C_INTEGRATION", "text": "Created event: review at 2pm."},
        },
    ]
