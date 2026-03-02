# Outlook Calendar Client Implementation

## Overview

## Purpose

## Architecture

## API Reference

### OutlookClient
Implements the `calendar_client_api.Client` abstract base class.

#### Methods

- `delete_event(event_id: str) -> None`: Deletes an event on the Outlook Calendar
- `list_events(*, start, end, types) -> list[Event]`: Returns calendar events with optional filters 
