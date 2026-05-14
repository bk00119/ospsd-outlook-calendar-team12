"""Pytest configuration for Outlook Calendar Client E2E tests.

This file provides:
- A single switch to enable/disable E2E runs (default: disabled)
- A session-scoped real client fixture
- Run ID + naming helpers to avoid polluting real calendars
- Best-effort cleanup for events created during a test session
- A small retry helper to handle Graph eventual consistency

Enable E2E locally:
    E2E=1 E2E_INTERACTIVE=1 pytest -m e2e --no-cov

Manual run (non-interactive, assuming token cache / service credentials are configured):
    E2E=1 pytest -m e2e --no-cov

Required env vars (for real auth):
    AZURE_CLIENT_ID
    AZURE_AUTHORITY

"""

from __future__ import annotations

import contextlib
import importlib
import os
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from typing import Protocol

    from calendar_client_api.client import Client

    class ClientFactory(Protocol):
        """Callable protocol for constructing an abstract calendar client."""

        def __call__(self, *, interactive: bool = False) -> object:
            """Build a client instance for E2E tests."""

import pytest


@dataclass(frozen=True)
class E2EConfig:
    """Configuration derived from environment variables for E2E tests."""

    enabled: bool
    interactive: bool
    client_id: str | None
    authority: str | None


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_e2e_config() -> E2EConfig:
    return E2EConfig(
        enabled=_truthy(os.getenv("E2E")) or _truthy(os.getenv("RUN_E2E")),
        interactive=_truthy(os.getenv("E2E_INTERACTIVE")),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        authority=os.getenv("AZURE_AUTHORITY"),
    )


def _resolve_factory_path(raw_factory: str) -> str:
    """Resolve a short E2E client factory alias to its fully qualified import path."""
    aliases = {
        "local": "outlook_client_impl.outlook_impl:get_client_impl",
        "service": "outlook_service_client_adapter.adapter:get_client_impl",
    }
    return aliases.get(raw_factory, raw_factory)


def _load_client_factory() -> ClientFactory:
    """Load the configured client factory for E2E tests.

    The factory is resolved lazily so that test consumer code depends only on the
    abstract calendar client contract, while the concrete implementation is injected
    via configuration.
    """
    raw_factory = os.getenv("E2E_CLIENT_FACTORY", "local")
    factory_path = _resolve_factory_path(raw_factory)

    module_name, sep, attr_name = factory_path.partition(":")
    if not sep or not module_name or not attr_name:
        msg = "E2E_CLIENT_FACTORY must be in the form 'package.module:callable_name'"
        raise RuntimeError(msg)

    module = importlib.import_module(module_name)
    factory = getattr(module, attr_name, None)
    if factory is None or not callable(factory):
        msg = f"Unable to load callable client factory from {factory_path!r}"
        raise RuntimeError(msg)


    return cast("ClientFactory", factory)


# Helper to detect if using service adapter factory
def _is_service_factory(factory_path: str) -> bool:
    """Detect if the configured factory is a service adapter."""
    return "adapter" in factory_path


@pytest.fixture(scope="session")
def client_factory() -> ClientFactory:
    """Return the injected client factory for E2E tests."""
    return _load_client_factory()


def pytest_configure(config: pytest.Config) -> None:
    """Register pytest markers used by the E2E test suite."""
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests",
    )
    config.addinivalue_line(
        "markers",
        "graph_e2e: E2E tests that call real Microsoft Graph",
    )
    config.addinivalue_line(
        "markers",
        "slow: tests that are slow / require external dependencies",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip E2E tests by default unless explicitly enabled via env vars."""
    _ = config
    e2e_cfg = _load_e2e_config()
    if e2e_cfg.enabled:
        return

    skip_e2e = pytest.mark.skip(
        reason="E2E tests are disabled. Set E2E=1 (and optionally E2E_INTERACTIVE=1).",
    )
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def e2e_config() -> E2EConfig:
    """Session-scoped E2E configuration."""
    cfg = _load_e2e_config()

    if not cfg.enabled:
        pytest.skip(
            "E2E tests are disabled. Set E2E=1 (and optionally E2E_INTERACTIVE=1).",
        )

    raw_factory = os.getenv("E2E_CLIENT_FACTORY", "local")
    factory_path = _resolve_factory_path(raw_factory)

    # Only require Azure env for local impl.
    if not _is_service_factory(factory_path):
        missing: list[str] = []
        if not cfg.client_id:
            missing.append("AZURE_CLIENT_ID")
        if not cfg.authority:
            missing.append("AZURE_AUTHORITY")

        if missing:
            pytest.skip(f"Missing required env var(s) for E2E: {', '.join(missing)}")
    else:
        base_url = os.getenv("OUTLOOK_CLIENT_SERVICE_BASE_URL", os.getenv("BASE_URL"))
        if not base_url:
            pytest.skip(
                "Service-adapter E2E requires OUTLOOK_CLIENT_SERVICE_BASE_URL or BASE_URL.",
            )

    return cfg


@pytest.fixture(scope="session")
def run_id(e2e_config: E2EConfig) -> str:
    """Generate a unique id for this E2E session to tag created events."""
    _ = e2e_config
    return uuid.uuid4().hex[:10]


@pytest.fixture
def client(
    client_factory: ClientFactory,
    e2e_config: E2EConfig,
) -> Client:
    """Real calendar client instance resolved through DI for E2E tests."""
    return cast("Client", client_factory(interactive=e2e_config.interactive))


@pytest.fixture
def created_event_ids() -> list[str]:
    """Collect event IDs created for best-effort cleanup."""
    return []


@pytest.fixture(autouse=True)
def _cleanup_created_events(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Best-effort cleanup for events created by Graph E2E tests.

    Black-box E2E tests should not construct a real calendar client.
    """
    if "graph_e2e" not in request.node.keywords:
        yield
        return

    client = cast("Client", request.getfixturevalue("client"))
    created_event_ids = cast(
        "list[str]",
        request.getfixturevalue("created_event_ids"),
    )

    yield

    for event_id in reversed(created_event_ids):
        with contextlib.suppress(Exception):
            client.delete_event(event_id)

    close_fn = getattr(client, "close", None)
    if callable(close_fn):
        with contextlib.suppress(Exception):
            close_fn()


@pytest.fixture
def e2e_title_prefix(run_id: str, request: pytest.FixtureRequest) -> str:
    """Build a standard title prefix for created events, including this session's run_id."""
    return f"[E2E][{run_id}][{request.node.name}]"


TIMEOUT_MSG = "Timed out waiting for condition in retry_until()"


def retry_until(
    predicate: Callable[[], object],
    *,
    timeout_s: float = 6.0,
    interval_s: float = 0.6,
) -> object:
    """Retry `predicate` until it returns a truthy value or timeout.

    Use this for Graph eventual-consistency behaviors (create/update then immediate read/list).

    Returns:
        The last truthy value returned by predicate.

    Raises:
        AssertionError: if timeout is reached.

    """
    deadline = time.time() + timeout_s
    last: object | None = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval_s)
    raise AssertionError(TIMEOUT_MSG)
