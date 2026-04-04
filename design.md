# Design Document

This document describes the architecture, design decisions, and component interactions for the Outlook Calendar Client project.

## 1. Goals

Build a calendar client that:

1. Separates the **interface contract** from **provider-specific logic**, so the implementation can be swapped (e.g., from Outlook to Google Calendar) without changing consumer code.
2. Follows strict code quality standards (Ruff, MyPy strict, 85% test coverage).
3. Is structured as a uv workspace so each component is an independently packaged Python library.

## 2. Architecture Overview

The system is composed of two components connected through dependency injection:
- `calendar_client_api`: Defines the abstract base class, `Client`, which is the contract of what the interface of a calendar client can do
- `outlook_client_impl`: Implements the `OutlookClient` class - a concrete implementation of the Calendar Client that uses Microsoft Graph to perform contract actions on Outlook Calendar

### Project Structure
```
OSPSD-OUTLOOK-CALENDAR-TEAM12/
├── src/                          # Source packages (uv workspace members)
│   ├── calendar_client_api/      # Abstract calendar client base class (ABC)
│   └── outlook_client_impl/      # Outlook Calendar specific client implementation
├── tests/                        # Integration and E2E tests
│   ├── integration/              # Component integration tests
│   └── e2e/                      # End-to-end application tests
├── docs/                         # Documentation source files
├── .circleci/                    # CircleCI configuration
├── main.py                       # Main application entry point
├── pyproject.toml                # Project configuration (dependencies, tools)
└── uv.lock                       # Locked dependency versions
```

## 3. Component Design

### 3.1 `calendar_client_api` — Abstract Interface

**Location:** `src/calendar_client_api/`

This package defines the contract that all calendar clients must implement. It contains:

- **`Client` (ABC):** Abstract base class with methods for CRUD operations on calendar events (`get_event`, `create_event`, `delete_event`, `update_event`, `list_events`).
- **`Event` (ABC):** Abstract base class defining event properties (`id`, `title`, `starts_at`, `ends_at`, `location`, `description`).
- **`EventPatch` (frozen dataclass):** A partial-update payload where all fields are optional. Only non-`None` fields are applied during an update.

**Design decision:** This package has zero external dependencies. It relies only on the Python standard library. This separates the interface contract with any provider specific api.

### 3.2 `outlook_client_impl` — Microsoft Graph Implementation

**Location:** `src/outlook_client_impl/`

This package provides the Outlook-specific implementation:

- **`OutlookClient(Client)`:** Concrete implementation that translates abstract method calls into Microsoft Graph API requests via `GraphServiceClient`.
- **`OutlookCalendarEvent(Event)`:** Concrete event that parses the JSON payload returned by Microsoft Graph into the abstract `Event` properties.
- **`AuthManager`:** MSAL-based authentication manager.

## 4. Testing Strategy


| Layer | Location | Purpose |
|---|---|---|
| Unit (API) | `src/calendar_client_api/tests/` | Interface contracts |
| Unit (Impl) | `src/outlook_client_impl/tests/` | OutlookClient with mocked Graph SDK |
| Integration | `tests/integration/` | Cross-component interactions |
| E2E | `tests/e2e/` | Full application flow |

### Coverage

Minimum 85% line coverage is enforced in CI.
