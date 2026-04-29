# Outlook Calendar Service

## Overview

`outlook_client_service` is the FastAPI service layer for our Outlook Calendar system.
It exposes the functionality of `outlook_client_impl` over HTTP endpoints and serves as
the main deployment unit for Homework 2.

This package is responsible for:
- exposing calendar operations as HTTP APIs,
- handling the OAuth 2.0 web flow,
- managing authenticated user sessions,
- providing health and service metadata endpoints for deployment and testing.

## Purpose

This package turns the local Outlook client implementation into a discoverable web service.

In the overall architecture:
- `calendar_client_api` defines the abstract contract,
- `outlook_client_impl` provides the local Microsoft Graph-backed implementation,
- `outlook_client_service` exposes that implementation over HTTP,
- `outlook_client_service_api_client` provides an auto-generated HTTP client,
- `outlook_client_adapter` preserves the original API contract while talking to the service.

The goal is location transparency: consumer code should be able to work with either the
local implementation or the service-backed adapter without changing its core usage pattern.

## Architecture

### Service Role

`outlook_client_service` is the deployment unit in the HW2 architecture.
It imports and uses the concrete implementation from `outlook_client_impl`
and exposes its core functionality through FastAPI routes.

The FastAPI application is created in `main.py` and registers three route groups:
- `health` for operational checks,
- `auth` for OAuth login and callback handling,
- `events` for calendar event operations.

### Authentication Flow

The service implements the OAuth 2.0 Authorization Code Flow for web applications.

At a high level:
1. the client visits `GET /auth/login`,
2. the service redirects the browser to Microsoft identity,
3. Microsoft redirects back to `GET /auth/callback`,
4. the service exchanges the authorization code for tokens,
5. token data is stored in the server-side session,
6. later event requests reuse the session and refresh the access token when needed.

The service currently requests these Microsoft Graph scopes:
- `offline_access`
- `https://graph.microsoft.com/Calendars.ReadWrite`

### Session Management

The application uses Starlette `SessionMiddleware` to store authentication state.
The session may contain:
- `access_token`
- `refresh_token`
- `expires_in`
- `expires_at`

When an event endpoint needs a Graph client, the dependency layer retrieves a valid access
token from the session. If the token is near expiration or missing, the service attempts
to refresh it using the stored refresh token before constructing the Graph client.

### Multi-User (Slack) Authentication

For Slack-based interactions, the service supports multi-user access without a database.

- The `/auth/login` endpoint accepts an optional `slack_user_id` query parameter.
- After OAuth completes, the user’s token data is bound in-memory to that Slack user ID.
- The Slack poller resolves the sender (`slack_user_id`) to a calendar session at runtime.

This design assumes a **single-instance deployment** with in-memory state.
### Dependency Injection

The service uses FastAPI dependency injection to provide configured services and shared
application state to route handlers.

The dependency layer in `dependencies.py` is responsible for:
- reading the authenticated session,
- validating or refreshing the current access token,
- building a Microsoft Graph client from that token,
- constructing an `OutlookClient` as a `calendar_client_api.client.Client` implementation.

This keeps route handlers thin and ensures that routing code depends on the abstract client
interface rather than directly embedding Graph setup logic.

## Slack Integration (Polling)

This service also supports a Slack-based interaction flow using a polling mechanism.

### Overview

The poller reads messages from a configured Slack channel and routes user requests
to the intelligent application service. Only messages that mention the bot
(e.g., `<@BOT_USER_ID>`) are processed.

Authentication is resolved per message using the sender's Slack user ID.

### Configuration

- `SLACK_BOT_USER_ID`: bot user ID for mention detection  
- `SLACK_TEST_CHANNEL_ID`: channel to monitor  
- `SLACK_USER_TIMEZONE` (optional): default timezone (default: `America/New_York`)

### Notes

- Uses polling instead of webhooks  
- Assumes single-instance with in-memory state  
- User timezone is not available via chat API, so a default is used  

### Entry Point

The polling loop is implemented in:

```
outlook_client_service/slack_poller.py
```

A simple runner script can be used to start the poller during development.


## Project Structure

```text
src/outlook_client_service/
├── routers/
│   ├── auth.py
│   ├── events.py
│   └── health.py
├── schemas/
│   ├── __init__.py
│   └── event.py
├── config.py
├── dependencies.py
├── main.py
└── py.typed
```

## Key Modules
- `main.py`: creates the FastAPI app, configures middleware, and registers routers.
- `config.py`: defines the Settings dataclass and loads environment-driven configuration.
- `dependencies.py`: provides dependency helpers for authentication, Graph client creation,
and interface-backed client construction.
- `routers/auth.py`: implements login, callback, logout, token refresh, and session token helpers.
- `routers/events.py`: exposes CRUD-style event endpoints backed by the calendar client interface.
- `routers/health.py`: provides a basic liveness endpoint.
- `schemas/`: contains request and response models for the HTTP API.

## API Endpoints

### Root Endpoint
- `GET /`  
  - Redirects to /auth/login.

### Health Endpoint
- `GET /health`
  - Returns 200 OK with {"status": "ok"}.

### Auth Endpoints
- `GET /auth/login`
  - Redirects the user to Microsoft’s authorization page.
  - GET /auth/callback
  - Accepts the authorization code from Microsoft, exchanges it for tokens, and stores
  token data in the session.
- `POST /auth/logout`
  - Clears the current session.

### Event Endpoints

All event endpoints depend on an authenticated session and build a calendar client through
FastAPI dependencies.
- `GET /events/`
  - Lists calendar events.
  - Optional query parameters: 
    - start: datetime | None 
    - end: datetime | None 
    - types: list[str] | None
- `POST /events/` 
  - Creates a new event.
- `GET /events/{event_id}` 
  - Retrieves a single event by ID. 
- `PATCH /events/{event_id}` 
  - Updates an existing event partially. 
- `DELETE /events/{event_id}`
  - Deletes an event and returns 204 No Content on success.

## Request and Response Models

The service uses schema models under outlook_client_service.schemas.event to separate
its HTTP contract from the internal implementation.

Current route handlers use:
- EventCreateRequest
- EventUpdateRequest
- EventResponse

The router converts calendar_client_api.event.Event objects into HTTP-facing
EventResponse objects before returning them to clients.

## Configuration

Configuration is defined in config.py through a frozen Settings dataclass.
Environment variables are loaded with python-dotenv.

### Main Settings
- BASE_URL 
  - Default: http://localhost:8000 
- AZURE_CLIENT_ID 
- AZURE_CLIENT_SECRET 
- AZURE_REDIRECT_URI 
  - Default: http://localhost:8000/auth/callback 
- AZURE_AUTHORITY 
  - Default: https://login.microsoftonline.com/consumers 
- SESSION_SECRET_KEY 
  - Default: dev-secret-key 
- CORS_ORIGINS 
  - Default: http://localhost:8000 
  - Parsed as a comma-separated list

## Running Locally

### Requirements
- Python 3.12+
- uv
- valid Microsoft application credentials

### Install dependencies
`uv sync`

### Set up environment variables

### Start the service
` uv run uvicorn outlook_client_service.main:app --reload`

Once the service is running, you can open `http://localhost:8000/auth/login` to login with your outlook account.
Then, open `http://localhost:8000/docs` to view and try the apis.