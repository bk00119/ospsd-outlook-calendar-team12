"""E2E tests for listing events.

Manual run (interactive auth):
    E2E=1 E2E_INTERACTIVE=1 pytest -m e2e --no-cov

Manual run (non-interactive, if token cache / credentials are configured):
    E2E=1 pytest -m e2e --no-cov
"""

from __future__ import annotations

import datetime
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.graph_e2e, pytest.mark.slow]


TIMEOUT_MSG = "Timed out waiting for condition in retry_until()"
MISSING_EVENT_ID_MSG = "Event id is missing"


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def retry_until(
    predicate: Callable[[], Any],
    *,
    timeout_s: float = 12.0,
    interval_s: float = 1.0,
) -> Any:
    """Retry predicate until it returns truthy or timeout."""
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval_s)
    raise AssertionError(TIMEOUT_MSG)


def _event_id(ev: Any) -> str:
    value = getattr(ev, "id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    value = getattr(ev, "event_id", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise AssertionError(MISSING_EVENT_ID_MSG)


def test_list_events_includes_created_event_in_time_window(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Create an event and verify list_events can retrieve it using a narrow window."""
    start = _utc_now() + datetime.timedelta(minutes=30)
    end = start + datetime.timedelta(minutes=10)

    created = client.create_event(
        f"{e2e_title_prefix} list-window",
        start,
        end,
        location="E2E Location",
        description="E2E Description",
    )
    eid = _event_id(created)
    created_event_ids.append(eid)

    def _listed_ids() -> set[str] | None:
        events = client.list_events(
            start=start - datetime.timedelta(minutes=1),
            end=end + datetime.timedelta(minutes=1),
        )
        ids = {_event_id(e) for e in events}
        return ids if eid in ids else None

    ids = retry_until(_listed_ids)
    assert eid in ids


def test_list_events_start_end_filters_work(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Verify start/end filters exclude events outside the range."""
    base = _utc_now() + datetime.timedelta(minutes=60)

    early_start = base
    early_end = early_start + datetime.timedelta(minutes=10)
    late_start = base + datetime.timedelta(minutes=40)
    late_end = late_start + datetime.timedelta(minutes=10)

    early = client.create_event(
        f"{e2e_title_prefix} list-filter early",
        early_start,
        early_end,
        location="E2E Location",
        description="E2E Description",
    )
    late = client.create_event(
        f"{e2e_title_prefix} list-filter late",
        late_start,
        late_end,
        location="E2E Location",
        description="E2E Description",
    )

    early_id = _event_id(early)
    late_id = _event_id(late)
    created_event_ids.extend([early_id, late_id])

    # Window only includes the late event.
    window_start = base + datetime.timedelta(minutes=30)
    window_end = base + datetime.timedelta(minutes=70)

    def _listed_ids() -> set[str] | None:
        events = client.list_events(start=window_start, end=window_end)
        ids = {_event_id(e) for e in events}
        return ids if late_id in ids else None

    ids = retry_until(_listed_ids)
    assert late_id in ids
    assert early_id not in ids


def test_list_events_types_filter_single_instance(
    client: Any,
    created_event_ids: list[str],
    e2e_title_prefix: str,
) -> None:
    """Types filter shouldn't drop our normal singleInstance event."""
    start = _utc_now() + datetime.timedelta(minutes=120)
    end = start + datetime.timedelta(minutes=10)

    created = client.create_event(
        f"{e2e_title_prefix} list-types",
        start,
        end,
        location="E2E Location",
        description="E2E Description",
    )
    eid = _event_id(created)
    created_event_ids.append(eid)

    def _listed_ids() -> set[str] | None:
        events = client.list_events(
            start=start - datetime.timedelta(minutes=1),
            end=end + datetime.timedelta(minutes=1),
            types=["singleInstance"],
        )
        ids = {_event_id(e) for e in events}
        return ids if eid in ids else None

    ids = retry_until(_listed_ids)
    assert eid in ids
