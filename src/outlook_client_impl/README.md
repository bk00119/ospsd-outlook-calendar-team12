# Outlook Client Implementation

## `list_events` — Jaik

`OutlookClient.list_events` fetches calendar events from Outlook with optional filters:

- `start` — drop events that start before this datetime
- `end` — drop events that end after this datetime
- `types` — only keep events matching the given type(s), e.g. `["singleInstance", "occurrence"]`

All filters are optional. Calling `list_events()` with no args returns everything.
