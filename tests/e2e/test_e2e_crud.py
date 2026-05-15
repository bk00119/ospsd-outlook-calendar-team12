"""E2E smoke tests for Outlook calendar event CRUD.

These tests call the real Microsoft Graph API through our Outlook client.

Manual run (interactive auth):
    E2E=1 E2E_INTERACTIVE=1 pytest -m e2e --no-cov

Manual run (non-interactive, if token cache / credentials are configured):
    E2E=1 pytest -m e2e --no-cov
"""

from __future__ import annotations

import contextlib
import datetime
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest
from calendar_client_api.exceptions import (
    CalendarNotFoundError,
    CalendarValidationError,
)

from calendar_client_api import event

TIMEOUT_MSG = "Timed out waiting for condition in retry_until()"

def _missing_attr_msg(obj: Any, names: tuple[str, ...]) -> str:
    return f"Object {type(obj)!r} missing any of attributes: {names!r}"


def retry_until(
    predicate: Callable[[], Any],
    *,
    timeout_s: float = 6.0,
    interval_s: float = 0.6,
) -> Any:
    """Retry `predicate` until it returns a truthy value or timeout.

    Use this for Graph eventual-consistency behaviors (create/update then immediate read/list).

    Returns:
        The last truthy value returned by predicate.

    Raises:
        AssertionError: if timeout is reached.

    """
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval_s)
    raise AssertionError(TIMEOUT_MSG)


pytestmark = [pytest.mark.e2e, pytest.mark.graph_e2e, pytest.mark.slow]


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _safe_get_event(client: Any, event_id: str) -> Any | None:
    try:
        return client.get_event(event_id)
    except Exception:
        return None


def _get_attr(obj: Any, *names: str) -> Any:
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    msg = _missing_attr_msg(obj, names)
    raise AttributeError(msg)


def _assert_event_like(created: Any, fetched: Any) -> None:
    """Assert fetched event matches created event on core fields."""
    created_id = _get_attr(created, "id", "event_id")
    fetched_id = _get_attr(fetched, "id", "event_id")
    assert fetched_id == created_id

    created_title = _get_attr(created, "title", "subject")
    fetched_title = _get_attr(fetched, "title", "subject")
    assert fetched_title == created_title

    created_start = _get_attr(created, "starts_at", "start")
    fetched_start = _get_attr(fetched, "starts_at", "start")
    assert fetched_start == created_start

    created_end = _get_attr(created, "ends_at", "end")
    fetched_end = _get_attr(fetched, "ends_at", "end")
    assert fetched_end == created_end


def test_create_then_get_event_roundtrip(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Create an event and verify it can be retrieved with identical core fields."""
    starts_at = _utc_now() + datetime.timedelta(minutes=30)
    ends_at = starts_at + datetime.timedelta(minutes=15)

    created = client.create_event(
        f"{e2e_title_prefix} create-get roundtrip",
        starts_at,
        ends_at,
        location="E2E Location",
        description="E2E Description",
    )

    created_id = _get_attr(created, "id", "event_id")
    assert isinstance(created_id, str)
    assert created_id
    created_event_ids.append(created_id)

    fetched = retry_until(lambda: _safe_get_event(client, created_id))
    _assert_event_like(created, fetched)


def test_delete_then_get_event_not_found(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Create an event, delete it, and verify a subsequent get fails."""
    starts_at = _utc_now() + datetime.timedelta(minutes=60)
    ends_at = starts_at + datetime.timedelta(minutes=15)

    created = client.create_event(
        f"{e2e_title_prefix} delete-not-found",
        starts_at,
        ends_at,
        location="E2E Location",
        description="E2E Description",
    )

    created_id = _get_attr(created, "id", "event_id")
    assert isinstance(created_id, str)
    assert created_id
    created_event_ids.append(created_id)

    # Reduce flakes: ensure readable before deletion
    _ = retry_until(lambda: _safe_get_event(client, created_id))

    client.delete_event(created_id)

    # Avoid double-delete in session cleanup (best effort)
    with contextlib.suppress(ValueError):
        created_event_ids.remove(created_id)

    with pytest.raises(CalendarNotFoundError):
        client.get_event(created_id)


def test_update_rejects_empty_patch_payload(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Contract-level check: EventPatch must update at least one field."""
    starts_at = _utc_now() + datetime.timedelta(minutes=90)
    ends_at = starts_at + datetime.timedelta(minutes=15)

    created = client.create_event(
        f"{e2e_title_prefix} empty-patch",
        starts_at,
        ends_at,
        location="E2E Location",
        description="E2E Description",
    )

    created_id = _get_attr(created, "id", "event_id")
    assert isinstance(created_id, str)
    assert created_id
    created_event_ids.append(created_id)

    with pytest.raises(CalendarValidationError):
        client.update_event(created_id, event.EventPatch())
