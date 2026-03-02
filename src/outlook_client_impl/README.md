# Outlook Calendar Client Implementation

## Overview

`outlook_client_impl` provides a concrete `calendar_client_api.Client`
implementation backed by Microsoft Graph. It handles authentication,
calls the Outlook Calendar API, and returns
`outlook_client_impl.event_impl.OutlookCalendarEvent` objects.

## Purpose

This package is the Outlook integration layer for our calendar client system:

- Microsoft Graph Integration: Connects to Outlook Calendar via Graph SDK.
- Authentication: Handles OAuth authentication with interactive/non-interactive modes.
- ABC Implementation: Implements `calendar_client_api.Client`.
- Event Integration: Works with `OutlookCalendarEvent` for event hydration.
- Dependency Injection: Registers itself as the active implementation on import.

## Architecture

### Authentication Modes

- `interactive=True`: allows browser OAuth flow and persists token cache under `.auth/`.
- `interactive=False`: uses configured environment variables and existing token cache first.

### Dependency Injection

```python
import outlook_client_impl  # triggers registration

from calendar_client_api import get_client
client = get_client(interactive=False)
```

Importing `outlook_client_impl` calls `register()` and wires:
- `calendar_client_api.get_client -> get_client_impl`
- `calendar_client_api.get_event -> get_event_impl`

## API Reference

### OutlookClient
Implements the `calendar_client_api.Client` abstract base class.

#### Methods

- `create_event(title: str, starts_at: datetime, ends_at: datetime, location: str | None = None, description: str | None = None) -> Event`
  - Creates events through `me.events.post(...)`.
  - Uses typed Graph models (`Event`, `DateTimeTimeZone`, `ItemBody`, `Location`) for the request body.
- `get_event(event_id: str) -> Event`
- `list_events(*, start=None, end=None, types=None) -> list[Event]`
- `update_event(event_id: str, payload: EventPatch) -> Event`
- `delete_event(event_id: str) -> None`

### Factory Function

`get_client_impl(*, interactive: bool = False) -> calendar_client_api.Client`:
creates `OutlookClient` and is injected into `calendar_client_api.get_client`
during import.

## Usage Examples

### Basic Client Initialization

```python
import outlook_client_impl
from calendar_client_api import get_client

client = get_client(interactive=False)
```

### Create Event

```python
from datetime import UTC, datetime, timedelta

import outlook_client_impl
from calendar_client_api import get_client

client = get_client(interactive=False)

start = datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=10)
end = start + timedelta(minutes=30)

event = client.create_event(
    title="OSPSD demo event",
    starts_at=start,
    ends_at=end,
    location="Online",
    description="Created from demo code",
)
print(event.id)
```

### Retrieve Event by ID

```python
import outlook_client_impl
from calendar_client_api import get_client

client = get_client(interactive=False)
event = client.get_event("<event-id>")
print(event.title)
```

## Authentication Setup

Create a `.env` file in the repository root (do not commit):

```bash
AZURE_CLIENT_ID=<your-client-id>
AZURE_AUTHORITY=https://login.microsoftonline.com/consumers
```

Token cache is stored under `.auth/`.

## Testing Notes

```bash
uv run pytest src/outlook_client_impl/tests/ -q
uv run pytest src/outlook_client_impl/tests/ --cov=src --cov-report=term-missing
```

Unit tests use mocks/stubs (no real network calls). Integration and E2E tests
are located under `tests/integration/` and `tests/e2e/`.

## Graph Integration Details

### Scopes

The client uses:

```python
SCOPES = ["User.Read", "Calendars.ReadWrite"]
```

### Create Event Request Body

`create_event` builds a typed Microsoft Graph `Event` request body using:
- `DateTimeTimeZone` for start/end
- `Location` for location
- `ItemBody` with `BodyType.Text` for description
