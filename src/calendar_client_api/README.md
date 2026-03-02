# Calendar Client API

## Overview

`calendar_client_api` defines the `Client` abstract base class that every calendar client must implement. The package contains the abstraction, a factory hook, and no concrete logic.

## Purpose

- Document the operations available to consumers.
- Provide a single factory (`get_client`) that implementations can override.
- Keep event-type dependencies explicit through the `calendar_client_api.event` module.
- Define the basic event operations (`create_event`, `get_event`, `delete_event`, `update_event`, `list_events`) every client must support.

## Architecture

### Component Design

`calendar_client_api` is a pure abstraction layer.

It defines:
- The `Client` abstract base class (ABC)
- The `Event` abstraction
- A factory hook (`get_client`) for runtime binding

This package contains **no provider-specific logic**. It is strictly separated from any concrete implementation

## API Reference

### Client (Abstract Base Class)

The `Client` defines the contract of the calendar client interface.

Methods:

- `create_event(title: str, starts_at: datetime, ends_at: datetime, location: str | None = None, description: str | None = None) -> Event`
- `get_event(event_id: str) -> Event`
- `delete_event(event_id: str) -> None`
- `update_event(event_id: str, payload: EventPatch) -> Event`
- `list_events(...) -> Iterable[Event]`
  
### Factory Function

`get_client(*, interactive: bool = False) -> Client`

Returns the bound implementation or raises `NotImplementedError`
if no implementation has registered itself.

## Dependencies

This package depends only on:
- Python standard library
- Internal `event` abstraction

It does **not** depend on any specific provider logic.


## Testing

```bash
uv run pytest src/calendar_client_api/tests/ -q
uv run pytest src/calendar_client_api/tests/ --cov=src/calendar_client_api --cov-report=term-missing
```

### `list_events`

`list_events` takes three optional keyword-only filters: `start`, `end`, and `types`. All are optional — no filters means return everything.

- `start` — only return events that start at or after this datetime
- `end` — only return events that end at or before this datetime
- `types` — only return events whose type matches (e.g. `"singleInstance"`, `"occurrence"`)
