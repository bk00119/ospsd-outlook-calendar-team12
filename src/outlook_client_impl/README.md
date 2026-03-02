# Outlook Calendar Client Implementation

## Overview

## Purpose

## Architecture

## API Reference

### OutlookClient
Implements the `calendar_client_api.Client` abstract base class.

#### Methods

- `delete_event(event_id: str) -> None`: Deletes an event on the Outlook Calendar
- `list_events(*, start, end, types) -> list[Event]`: Returns calendar events with optional filters (Jaik)

## `list_events` — Jaik

`OutlookClient.list_events` fetches calendar events from Outlook with optional filters:

- `start` — drop events that start before this datetime
- `end` — drop events that end after this datetime
- `types` — only keep events matching the given type(s), e.g. `["singleInstance", "occurrence"]`

All filters are optional. Calling `list_events()` with no args returns everything.
