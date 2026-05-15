"""Black-box E2E tests for the deployed service entry point."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import pytest
import requests

if TYPE_CHECKING:
    from collections.abc import Iterator

E2E_TIMEOUT_SECONDS = 20
E2E_POLL_INTERVAL_SECONDS = 0.25

pytestmark = pytest.mark.e2e


def _wait_until_remote_ready(base_url: str) -> None:
    """Wait until a deployed service responds to health checks."""
    deadline = time.time() + E2E_TIMEOUT_SECONDS
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == HTTPStatus.OK:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(E2E_POLL_INTERVAL_SECONDS)

    err_msg = f"Remote service did not become ready: {last_error}"
    raise TimeoutError(err_msg)


@dataclass(frozen=True)
class RunningService:
    """Represents a locally running black-box service process."""

    base_url: str
    process: subprocess.Popen[str] | None = None


def _get_free_port() -> int:
    """Return an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_until_ready(base_url: str, process: subprocess.Popen[str]) -> None:
    """Wait until the service responds to health checks."""
    deadline = time.time() + E2E_TIMEOUT_SECONDS
    last_error: Exception | None = None

    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            err_msg = (
                "Service subprocess exited before becoming ready.\n"
                f"stdout:\n{stdout}\n"
                f"stderr:\n{stderr}"
            )
            raise RuntimeError(err_msg)
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == HTTPStatus.OK:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(E2E_POLL_INTERVAL_SECONDS)

    err_msg = f"Service did not become ready: {last_error}"
    raise TimeoutError(err_msg)


@pytest.fixture(scope="module")
def running_service() -> Iterator[RunningService]:
    """Start the FastAPI app as a subprocess and stop it after tests."""
    remote_base_url = os.getenv("E2E_BASE_URL")
    if remote_base_url:
        base_url = remote_base_url.rstrip("/")
        _wait_until_remote_ready(base_url)
        yield RunningService(base_url=base_url)
        return

    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        {
            "APP_BASE_URL": base_url,
            "BASE_URL": base_url,
            "AZURE_AUTHORITY": "https://login.microsoftonline.com/consumers",
            "AZURE_CLIENT_ID": "blackbox-e2e-client-id",
            "AZURE_CLIENT_SECRET": "blackbox-e2e-client-secret",
            "AZURE_REDIRECT_URI": f"{base_url}/auth/callback",
            "ENABLE_SLACK_POLLER": "false",
            "OTEL_SDK_DISABLED": "true",
            "SESSION_SECRET_KEY": "blackbox-e2e-session-secret",
        },
    )

    # The command is fixed and all dynamic values are controlled by this test.
    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "uvicorn",
            "outlook_client_service.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _wait_until_ready(base_url, process)
        yield RunningService(base_url=base_url, process=process)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_health_endpoint_responds_from_subprocess(running_service: RunningService) -> None:
    """Verify the deployed app entry point exposes the health endpoint."""
    response = requests.get(f"{running_service.base_url}/health", timeout=5)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_login_from_subprocess(running_service: RunningService) -> None:
    """Verify the root path exposes the user-visible login redirect."""
    response = requests.get(
        running_service.base_url,
        timeout=5,
        allow_redirects=False,
    )

    assert response.status_code in {HTTPStatus.TEMPORARY_REDIRECT, HTTPStatus.FOUND}
    assert response.headers["location"] == "/auth/login"


def test_login_redirects_to_provider_from_subprocess(
    running_service: RunningService,
) -> None:
    """Verify login redirects to the OAuth provider and stores state in session."""
    session = requests.Session()

    response = session.get(
        f"{running_service.base_url}/auth/login",
        timeout=5,
        allow_redirects=False,
    )

    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)

    assert response.status_code in {HTTPStatus.TEMPORARY_REDIRECT, HTTPStatus.FOUND}
    assert parsed.scheme == "https"
    assert parsed.netloc == "login.microsoftonline.com"
    assert parsed.path.endswith("/oauth2/v2.0/authorize")
    assert "client_id" in query
    assert query["client_id"][0]
    assert "redirect_uri" in query
    assert query["redirect_uri"][0].endswith("/auth/callback")
    assert "state" in query
    assert "session" in session.cookies


def test_callback_missing_code_returns_user_visible_error(
    running_service: RunningService,
) -> None:
    """Verify callback error handling through the HTTP boundary."""
    response = requests.get(
        f"{running_service.base_url}/auth/callback",
        timeout=5,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["detail"] == "Missing authorization code."


def test_list_events_requires_auth_from_subprocess(
    running_service: RunningService,
) -> None:
    """Verify listing events requires authentication through the HTTP boundary."""
    response = requests.get(
        f"{running_service.base_url}/events/",
        timeout=5,
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "refresh token" in response.json()["detail"].lower()


def test_create_event_requires_auth_from_subprocess(
    running_service: RunningService,
) -> None:
    """Verify creating events requires authentication through the HTTP boundary."""
    response = requests.post(
        f"{running_service.base_url}/events/",
        json={
            "title": "Black-box E2E Event",
            "starts_at": "2026-05-14T09:00:00-04:00",
            "ends_at": "2026-05-14T10:00:00-04:00",
            "location": "Test Room",
            "description": "Created by black-box E2E test.",
        },
        timeout=5,
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "refresh token" in response.json()["detail"].lower()
