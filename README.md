# Team 12: Outlook (Calendar)

[![Coverage](https://img.shields.io/badge/coverage-85%2B%25-brightgreen)](https://circleci.com/gh/bk00119/ospsd-outlook-calendar-team12)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Team Members

- Brian Kim (hk2994)
- Ian Cheng (yc7162)
- Jaik Tom (jkt6063)
- Tingran Zhang (tz2906)
- Anastasia Strulistova (as14244)

# Outlook Calendar Client
This repository implements a component based client for calendar applications with concrete integration with Microsoft Outlook Calendar.

The project emphasizes interface and implementation separation, dependency injection, strict tooling and automated testing.

## Architecture Overview
The project emphasizes independence between client interface (a contract) and the implementation, creating a separation thus allowing:
- Only understanding the (simple) interface as a requisite to using the client,
- Changing implementation to a different Calendar provider without breaking existing code.

Implementation is injected into the contract at runtime through Dependency Injection

## AI and Cross-Vertical Chat Integration

This service combines three modular layers: the Outlook calendar client (our vertical), an AI orchestration layer, and a Slack chat integration (cross-vertical). Each layer talks only to interfaces defined elsewhere, so providers are swappable without touching the consumer code.

### AI Integration

`IntelligentAppService` (in `src/intelligent_app_service/`) orchestrates a Google Gemini LLM with **tool calling** enabled. Four typed calendar tools are exposed to the model:

| Tool | Behavior |
|---|---|
| `create_outlook_event` | Creates an event; refuses if the requested window conflicts with an existing event |
| `list_my_events` | Returns a formatted natural-language summary of events in a time range |
| `get_outlook_event` | Returns details of a specific event |
| `update_outlook_event` | Updates an event; refuses if a time change would conflict with another event |

The destructive `delete_event` tool is **intentionally not exposed** to the model to prevent accidental data loss from misclassified prompts. AI provider credentials are loaded from `GEMINI_API_KEY` at startup — never hardcoded.

### Cross-Vertical Chat Integration

The service depends on the chat vertical's shared `chat-client-api` ABC, pulled from [`HarshithKoriRaj/Shared-API`](https://github.com/HarshithKoriRaj/Shared-API). A local `Team12SlackClient` adapter (`src/outlook_client_service/.../slack_chat_client.py`) wraps `slack-sdk` and implements the ABC, registering itself with `register_client(...)` on import.

Application code only imports the `ChatClient` ABC — Slack-specific code is isolated to the adapter, satisfying the rubric's swappability requirement.

**Two trigger paths feed user messages into the AI:**

- **HTTP `/chat`**: A POST endpoint accepting `{message, channel_id, timezone}`. The AI response is forwarded to the requested Slack channel via the registered chat client.
- **Slack poller** (`slack_poller.py`): Opt-in background loop gated behind `ENABLE_SLACK_POLLER=true`. Watches a Slack channel for bot mentions and routes them through the same `IntelligentAppService.process_chat()` path.

### Why a Local Slack Adapter (instead of pulling Team 9's `slack-client-impl`)

The Slack team's published `slack-client-impl` package internally declares its `chat-client-api` dependency pointing at `HarshithKoriRaj/CS-GY-9223-Open-Source` (their working repo). Our project pulls `chat-client-api` from the canonical `HarshithKoriRaj/Shared-API` repo, which causes `uv` to refuse resolution due to two different Git URLs for the same package name. The local adapter sidesteps this cleanly while still depending only on the shared ABC.

### Core Components
- `calendar_client_api`: Defines the abstract base class, `Client`, which is the contract of what the interface of a calendar client can do
- `outlook_client_impl`: Implements the `OutlookClient` class - a concrete implementation of the Calendar Client that uses Microsoft Graph to perform contract actions on Outlook Calendar

### Service Components
- `outlook_client_service`: FastAPI service that exposes the calendar operations over HTTP with OAuth 2.0 authentication
- `outlook_client_service_api_client`: Auto-generated Python client created from the service's OpenAPI spec
- `outlook_service_client_adapter`: Adapter that implements the `Client` ABC by delegating to the generated client, enabling location-transparent usage

### AI Components
- `ai_client_api`: Abstract `AIClient` interface for text-generation and structured-generation requests; framework-free and provider-agnostic
- `gemini_ai_client_impl`: Concrete implementation backed by Google Gemini via the official `google-genai` SDK
- `intelligent_app_service`: AI orchestration layer that exposes calendar tools to the model and routes natural-language messages through the registered `AIClient`

### Cross-Vertical Chat Components
- `chat-client-api` (external dep from [HarshithKoriRaj/Shared-API](https://github.com/HarshithKoriRaj/Shared-API)): The shared `ChatClient` ABC agreed upon by the chat vertical
- `outlook_client_service/slack_chat_client.py`: Local `Team12SlackClient` adapter that wraps the official `slack-sdk` and implements `ChatClient`. Registers itself via `register_client(...)` on import
- `outlook_client_service/slack_poller.py`: Opt-in background poller (gated by `ENABLE_SLACK_POLLER`) that forwards Slack bot mentions through `IntelligentAppService.process_chat()`

### Project Structure
```
OSPSD-OUTLOOK-CALENDAR-TEAM12/
├── src/
│   ├── calendar_client_api/              # Calendar ABC (our vertical's shared interface)
│   ├── outlook_client_impl/              # Microsoft Graph implementation
│   ├── outlook_client_service/           # FastAPI service (auth, events, /chat, slack_poller)
│   ├── outlook_client_service_api_client/# Auto-generated HTTP client
│   ├── outlook_service_client_adapter/   # Adapter back to Client ABC
│   ├── ai_client_api/                    # AIClient ABC (provider-agnostic)
│   ├── gemini_ai_client_impl/            # Google Gemini implementation
│   └── intelligent_app_service/          # AI orchestration + tool dispatch
├── tests/
│   ├── integration/                      # DI wiring, adapter, and cross-vertical tests
│   └── e2e/                              # End-to-end tests (local + deployed)
├── docs/                                 # MkDocs documentation source
├── .circleci/                            # CircleCI configuration
├── fly.toml                              # Fly.io IaC declaration
├── DESIGN.md                             # Detailed architecture / design doc
├── pyproject.toml                        # Workspace config (dependencies, tools)
└── uv.lock                              # Locked dependency versions
```

## Project Setup
### 1. Prerequisites

- Python 3.12 or higher
- `uv` - Python package manager

### 2. Initial Setup

1.  **Install `uv`:**
    ```bash
    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Windows (PowerShell)
    irm https://astral.sh/uv/install.ps1 | iex
    ```

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <repo-name>
    ```

3.  **Set Up Azure Credentials:**
    - Register an application in [Azure Portal](https://portal.azure.com/) with `Calendars.ReadWrite` and `User.Read` delegated permissions.
    - Create a `.env` file in the project root with:
        ```bash
        AZURE_CLIENT_ID="your-azure-client-id"
        AZURE_AUTHORITY="https://login.microsoftonline.com/consumers"
        ```
    - For CI/CD environments, set these as environment variables directly.
    - **Important:** `.env` and `.auth/` contain secrets and are ignored by `.gitignore`.

4.  **Create and Sync the Virtual Environment:**
    This single command creates a `.venv` folder and installs all packages (including workspace members and development tools) defined in `uv.lock`.
    ```bash
    uv sync --all-packages --extra dev
    ```

5.  **Activate the Virtual Environment:**
    ```bash
    # macOS / Linux
    source .venv/bin/activate
    # Windows (PowerShell)
    .venv\Scripts\Activate.ps1
    ```

## Running the Toolchain

- **Linting & Formatting (Ruff):**
    ```bash
    # Check for issues
    uv run ruff check .
    # Automatically fix issues
    uv run ruff check . --fix
    # Format
    uv run ruff format .
    ```

- **Static Type Checking (MyPy):**
    ```bash
    uv run mypy src/ 
    ```

- **Testing (Pytest):**
    ```bash
    # All tests
    uv run pytest

    # Unit tests only (fast, no credentials needed)
    uv run pytest src/

    # Run integration tests
    uv run pytest -m integration

    # Run black-box end-to-end tests (local subprocess)
    # Starts the FastAPI app as a subprocess and validates user-visible HTTP behavior.
    E2E=1 \
    uv run pytest tests/e2e/test_service_blackbox.py --no-cov

    # Run black-box end-to-end tests against the deployed service
    E2E=1 \
    E2E_BASE_URL=https://ospsd-outlook-calendar-team12.fly.dev \
    uv run pytest tests/e2e/test_service_blackbox.py --no-cov

    # Run Graph-backed end-to-end tests on the local library
    E2E=1 \
    E2E_CLIENT_FACTORY=local \
    uv run pytest -m graph_e2e --no-cov

    # Run Graph-backed end-to-end tests on the HTTP service adapter
    # Before running this, authenticate once in your browser,
    # then copy the session cookie value into the variable below.
    E2E=1 \
    E2E_CLIENT_FACTORY=service \
    OUTLOOK_CLIENT_SERVICE_BASE_URL=http://localhost:8000 \
    OUTLOOK_CLIENT_SERVICE_SESSION='...' \
    uv run pytest -m graph_e2e --no-cov

    # Same, against the deployed Fly.io instance
    E2E=1 \
    E2E_CLIENT_FACTORY=service \
    OUTLOOK_CLIENT_SERVICE_BASE_URL=https://ospsd-outlook-calendar-team12.fly.dev \
    OUTLOOK_CLIENT_SERVICE_SESSION='...' \
    uv run pytest -m e2e --no-cov

    # With coverage report
    uv run pytest --cov=src --cov-report=term-missing
    ```

- **Documentation (MkDocs):**
    ```bash
    uv run mkdocs serve
    ```
    Open your browser to `http://127.0.0.1:8000` to view the site.

## Running the Service Locally

```bash
uv run uvicorn outlook_client_service.main:app --reload
```

The service will be available at `http://localhost:8000`. Visit `/docs` for the interactive API documentation.

**Required environment variables:**

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Azure app registration client ID |
| `AZURE_CLIENT_SECRET` | Azure app registration client secret |
| `AZURE_AUTHORITY` | `https://login.microsoftonline.com/consumers` |
| `SESSION_SECRET_KEY` | Required in production for session middleware (a dev fallback is generated locally when unset) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `GEMINI_API_KEY` | Google Gemini API key for the AI client |
| `SLACK_BOT_TOKEN` | Slack bot OAuth token (`xoxb-…`) for the chat adapter |
| `SLACK_AUTH_TOKEN` | Token used to authenticate Slack auth callbacks (avoids trusting raw `slack_user_id` from URLs) |
| `ENABLE_SLACK_POLLER` | `true` to enable the background Slack poller (default: `false`) |
| `CHAT_CLIENT_IMPL_MODULE` | Optional: name of a chat impl module to import at startup (e.g. our `outlook_client_service.slack_chat_client`); used only when no impl has been registered yet |

## Deployment

The service is deployed on [Fly.io](https://fly.io):

- **URL**: `https://ospsd-outlook-calendar-team12.fly.dev`
- **Health check**: `https://ospsd-outlook-calendar-team12.fly.dev/health`
- **OpenAPI spec**: `https://ospsd-outlook-calendar-team12.fly.dev/openapi.json`

Application secrets (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `GEMINI_API_KEY`,
`SESSION_SECRET_KEY`, etc.) are set via `fly secrets set KEY=value` and stored in
Fly.io's encrypted secrets manager — never committed to source control.

### Infrastructure as Code (fly.toml)

Deployment infrastructure is declared in [`fly.toml`](fly.toml) at the repo
root: app name, region, VM size, port mapping, HTTPS, healthcheck, and
auto-stop/auto-start policy. `flyctl deploy --config fly.toml` from a clean
state provisions and rolls the app, making the file the single source of
truth for Fly.io infrastructure.

### Telemetry (OpenTelemetry → Honeycomb)

The service is instrumented with OpenTelemetry for distributed tracing,
auto-emitted HTTP server metrics via `FastAPIInstrumentor`, and structured
JSON logging via `structlog`. Spans and metrics are shipped over OTLP/HTTP
to [Honeycomb](https://www.honeycomb.io) when `OTEL_EXPORTER_OTLP_ENDPOINT`
is set; otherwise they fall back to the console exporter for local
development.

- **Live dashboard**: <https://ui.honeycomb.io/ospds/environments/test/board/zfvxVA8cFfS>
  - Panel 1 — **P95 latency by route** (`P95(duration_ms)` GROUP BY `http.route`)
  - Panel 2 — **Request count by status code** (`COUNT` GROUP BY `http.status_code`)

Relevant env vars:

| Variable | Description |
|----------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP endpoint (e.g. `https://api.honeycomb.io`) |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth header (e.g. `x-honeycomb-team=<api-key>`) |
| `APP_ENV` | `prod` / `dev` — tagged on every span as `deployment.environment` |
| `APP_VERSION` | tagged on every span as `service.version` |

## Continuous Integration & Deployment

The project uses CircleCI (`.circleci/config.yml`) with two workflows:

- **All Branches**: Build, lint, unit tests, and CI-compatible integration tests
- **Main/Develop**: Additional integration tests with real Microsoft Graph API calls using credentials from the `outlook-client` CircleCI context

**Automatic Deployment**: Every push to the `hw-3` branch triggers the full CI pipeline in CircleCI. After lint and tests pass, CircleCI runs `flyctl deploy` to build the Docker image remotely and roll the new version onto Fly.io. Only passing builds are deployed.

**CI/CD Environment Variables** (set in CircleCI project settings):

| Variable | Description |
|----------|-------------|
| `FLY_API_TOKEN` | Fly.io deploy token (from `fly tokens create deploy`) |
| `AZURE_CLIENT_ID` | Azure app registration client ID |
| `AZURE_CLIENT_SECRET` | Azure app registration client secret |
| `AZURE_TENANT_ID` | Azure tenant ID |
