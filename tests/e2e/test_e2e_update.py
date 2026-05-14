"""E2E tests for Outlook calendar event updates (EventPatch).

Manual run (interactive auth):
    E2E=1 E2E_INTERACTIVE=1 pytest -m e2e --no-cov

Manual run (non-interactive, if token cache / credentials are configured):
    E2E=1 pytest -m e2e --no-cov
"""

from __future__ import annotations

import datetime
import html as html_lib
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from calendar_client_api import event

pytestmark = [pytest.mark.e2e, pytest.mark.graph_e2e, pytest.mark.slow]

TIMEOUT_MSG = "Timed out waiting for condition in retry_until()"
MISSING_EVENT_ID_MSG = "Event id is missing or not a string"
INVALID_TITLE_TYPE_MSG = "Event title is not a string"
INVALID_START_TYPE_MSG = "Event starts_at is not a datetime"
INVALID_END_TYPE_MSG = "Event ends_at is not a datetime"

def _missing_attr_msg(obj: Any, names: tuple[str, ...]) -> str:
    return f"Object {type(obj)!r} missing any of attributes: {names!r}"


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _floor_to_seconds(dt: datetime.datetime) -> datetime.datetime:
    """Normalize datetimes to second precision.

    Microsoft Graph / Exchange commonly drop microseconds when storing or returning
    event start/end timestamps. For stable E2E assertions we compare at second
    precision.
    """
    return dt.replace(microsecond=0)


def retry_until(
    predicate: Callable[[], Any],
    *,
    timeout_s: float = 8.0,
    interval_s: float = 0.8,
) -> Any:
    """Retry predicate until it returns truthy or timeout.

    Graph can be eventually consistent for reads right after writes.
    """
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval_s)
    raise AssertionError(TIMEOUT_MSG)


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

def _event_id(ev: Any) -> str:
    value = _get_attr(ev, "id", "event_id")
    if not isinstance(value, str) or not value.strip():
        raise TypeError(MISSING_EVENT_ID_MSG)
    return value


def _title(ev: Any) -> str:
    value = _get_attr(ev, "title", "subject")
    if not isinstance(value, str):
        raise TypeError(INVALID_TITLE_TYPE_MSG)
    return value


def _starts_at(ev: Any) -> datetime.datetime:
    value = _get_attr(ev, "starts_at", "start")
    if not isinstance(value, datetime.datetime):
        raise TypeError(INVALID_START_TYPE_MSG)
    return value


def _ends_at(ev: Any) -> datetime.datetime:
    value = _get_attr(ev, "ends_at", "end")
    if not isinstance(value, datetime.datetime):
        raise TypeError(INVALID_END_TYPE_MSG)
    return value


def _location(ev: Any) -> str | None:
    return getattr(ev, "location", None)


def _description(ev: Any) -> str | None:
    return getattr(ev, "description", None)


def _description_text(ev: Any) -> str | None:
    """Normalize description/body content to plain text.

    Outlook/Exchange may return the body as HTML even if we send plain text.
    This helper extracts readable text for stable E2E assertions.
    """
    raw = _description(ev)
    if raw is None:
        return None

    # Fast path: exact match / already plain text.
    if "<" not in raw and ">" not in raw:
        return raw.strip()

    # Common Exchange wrapper: <div class="PlainText">...</div>
    m = re.search(r"<div[^>]*class=\"PlainText\"[^>]*>(.*?)</div>", raw, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return html_lib.unescape(m.group(1)).strip()

    # Fallback: strip tags crudely and normalize whitespace.
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def test_update_title_only_preserves_other_fields(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Update only the title and verify other fields remain unchanged."""
    starts_at = _utc_now() + datetime.timedelta(minutes=45)
    ends_at = starts_at + datetime.timedelta(minutes=20)

    original = client.create_event(
        f"{e2e_title_prefix} update-title original",
        starts_at,
        ends_at,
        location="E2E Location A",
        description="E2E Description A",
    )
    eid = _event_id(original)
    created_event_ids.append(eid)

    patch = event.EventPatch(title=f"{e2e_title_prefix} update-title NEW")
    _ = client.update_event(eid, patch)

    fetched = retry_until(lambda: _safe_get_event(client, eid))

    assert _title(fetched) == f"{e2e_title_prefix} update-title NEW"
    assert _floor_to_seconds(_starts_at(fetched)) == _floor_to_seconds(_starts_at(original))
    assert _floor_to_seconds(_ends_at(fetched)) == _floor_to_seconds(_ends_at(original))

    assert _location(fetched) == _location(original)
    assert _description_text(fetched) == _description_text(original)


def test_update_description_and_location(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Update description and location and verify other fields remain unchanged."""
    starts_at = _utc_now() + datetime.timedelta(minutes=75)
    ends_at = starts_at + datetime.timedelta(minutes=20)

    original = client.create_event(
        f"{e2e_title_prefix} update-desc-loc original",
        starts_at,
        ends_at,
        location="E2E Location A",
        description="E2E Description A",
    )
    eid = _event_id(original)
    created_event_ids.append(eid)

    patch = event.EventPatch(description="E2E Description B", location="E2E Location B")
    _ = client.update_event(eid, patch)

    fetched = retry_until(lambda: _safe_get_event(client, eid))

    assert _title(fetched) == _title(original)
    assert _floor_to_seconds(_starts_at(fetched)) == _floor_to_seconds(_starts_at(original))
    assert _floor_to_seconds(_ends_at(fetched)) == _floor_to_seconds(_ends_at(original))

    assert _location(fetched) == "E2E Location B"
    assert _description_text(fetched) == "E2E Description B"


def test_update_time_window(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Update start/end times and verify the new time window is persisted."""
    starts_at = _utc_now() + datetime.timedelta(minutes=105)
    ends_at = starts_at + datetime.timedelta(minutes=20)

    original = client.create_event(
        f"{e2e_title_prefix} update-time original",
        starts_at,
        ends_at,
        location="E2E Location",
        description="E2E Description",
    )
    eid = _event_id(original)
    created_event_ids.append(eid)

    new_start = starts_at + datetime.timedelta(minutes=30)
    new_end = ends_at + datetime.timedelta(minutes=30)
    patch = event.EventPatch(starts_at=new_start, ends_at=new_end)
    _ = client.update_event(eid, patch)

    fetched = retry_until(lambda: _safe_get_event(client, eid))

    assert _floor_to_seconds(_starts_at(fetched)) == _floor_to_seconds(new_start)
    assert _floor_to_seconds(_ends_at(fetched)) == _floor_to_seconds(new_end)
    assert _title(fetched) == _title(original)
