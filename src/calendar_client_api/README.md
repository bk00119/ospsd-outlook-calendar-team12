# Calendar Client API

## Overview

`calendar_client_api` defines the `Client` abstract base class that every calendar client must implement. The package contains the abstraction, a factory hook, and no concrete logic.

## Purpose

- Document the operations available to consumers.
- Provide a single factory (`get_client`) that implementations can override.
- Keep event-type dependencies explicit through the `calendar_client_api.event` module.
- Define the basic event operations (`create_event`, `get_event`, `delete_event`, `update_event`, `list_events`) every client must support.


## Architecture

### `list_events`

`list_events` takes three optional keyword-only filters: `start`, `end`, and `types`. All are optional — no filters means return everything.

- `start` — only return events that start at or after this datetime
- `end` — only return events that end at or before this datetime
- `types` — only return events whose type matches (e.g. `"singleInstance"`, `"occurrence"`)
