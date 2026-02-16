# Calendar Client API

## Overview

`calendar_client_api` defines the `Client` abstract base class that every calendar client must implement. The package contains the abstraction, a factory hook, and no concrete logic.

## Purpose

- Document the operations available to consumers.
- Provide a single factory (`get_client`) that implementations can override.
- Keep event-type dependencies explicit through the `calendar_client_api.event` module.

## Architecture
