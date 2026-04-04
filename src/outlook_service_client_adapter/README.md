# Outlook Service Client Adapter

## Overview

`outlook_service_client_adapter` implements the `calendar_client_api.Client` ABC by delegating to the auto-generated HTTP client (`outlook_client_service_api_client`). This enables location transparency: consumer code can use either the local `OutlookClient` or this adapter without changing any application logic.

## Dependencies

- `calendar_client_api`: The abstract interface this package implements
- `outlook_client_service_api_client`: The auto-generated client that handles HTTP communication with the FastAPI service

## How It Works

The adapter translates each `Client` ABC method into a call on the corresponding generated client function:

| ABC Method | Generated Function |
|---|---|
| `get_event` | `get_event_events_event_id_get.sync` |
| `list_events` | `list_events_events_get.sync` |
| `create_event` | `create_event_events_post.sync` |
| `update_event` | `update_event_events_event_id_patch.sync` |
| `delete_event` | `delete_event_events_event_id_delete.sync` |

Responses from the generated client are mapped back into `Event`-compatible objects via `AdapterEvent`.

## Dependency Injection

Importing this package registers the adapter as the active `Client` implementation:

```python
import outlook_service_client_adapter  # triggers register()

from calendar_client_api import get_client
client = get_client()
client.delete_event("event-id")  # calls the FastAPI service over HTTP
```

## Testing

```bash
uv run pytest src/outlook_service_client_adapter/tests/ -q
```

Unit tests mock the generated client module functions. Integration tests in `tests/integration/` use `httpx.MockTransport` to verify the full adapter-to-HTTP path.
