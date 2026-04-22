# Team 12: Outlook (Calendar)

[![Coverage](https://img.shields.io/badge/coverage-85%2B%25-brightgreen)](https://circleci.com/gh/bk00119/ospsd-outlook-calendar-team12)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
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

### Core Components
- `calendar_client_api`: Defines the abstract base class, `Client`, which is the contract of what the interface of a calendar client can do
- `outlook_client_impl`: Implements the `OutlookClient` class - a concrete implementation of the Calendar Client that uses Microsoft Graph to perform contract actions on Outlook Calendar

### Service Components
- `outlook_client_service`: FastAPI service that exposes the calendar operations over HTTP with OAuth 2.0 authentication
- `outlook_client_service_api_client`: Auto-generated Python client created from the service's OpenAPI spec
- `outlook_service_client_adapter`: Adapter that implements the `Client` ABC by delegating to the generated client, enabling location-transparent usage

### Project Structure
```
OSPSD-OUTLOOK-CALENDAR-TEAM12/
├── src/
│   ├── calendar_client_api/              # Abstract client interface (ABC)
│   ├── outlook_client_impl/              # Microsoft Graph implementation
│   ├── outlook_client_service/           # FastAPI service
│   ├── outlook_client_service_api_client/# Auto-generated HTTP client
│   └── outlook_service_client_adapter/   # Adapter back to Client ABC
├── tests/
│   ├── integration/                      # DI wiring and adapter integration tests
│   └── e2e/                              # End-to-end tests
├── docs/                                 # MkDocs documentation source
├── .circleci/                            # CircleCI configuration
├── pyproject.toml                        # Workspace config (dependencies, tools)
└── uv.lock                              # Locked dependency versions
```

## Project Setup
### 1. Prerequisites

- Python 3.11 or higher
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

    # Run end to end tests on local library
    E2E=1 \
    E2E_CLIENT_FACTORY=local \
    uv run pytest -m e2e --no-cov
  
    # Run end to end tests on remote service
    # You can change the base url to the remote server address.
    # Before running this, please login with your browser first, then copy and paste the session value to the variable below.
    E2E=1 \
    E2E_CLIENT_FACTORY=service \
    OUTLOOK_CLIENT_SERVICE_BASE_URL=http://localhost:8000 \
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
| `SESSION_SECRET_KEY` | Secret key for session middleware |
| `CORS_ORIGINS` | Comma-separated allowed origins |

## Deployment

The service is deployed on [Fly.io](https://fly.io):

- **URL**: `https://ospsd-outlook-calendar-team12.fly.dev`
- **Health check**: `https://ospsd-outlook-calendar-team12.fly.dev/health`
- **OpenAPI spec**: `https://ospsd-outlook-calendar-team12.fly.dev/openapi.json`

Application secrets (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `GEMINI_API_KEY`,
`SESSION_SECRET_KEY`, etc.) are set via `fly secrets set KEY=value` and stored in
Fly.io's encrypted secrets manager — never committed to source control.

### Infrastructure as Code (Terraform)

The Fly.io app, dedicated IPs, and machine are declared as code in the
[`terraform/`](terraform/) directory and applied with Terraform. See
[`terraform/README.md`](terraform/README.md) for the `init`/`plan`/`apply` workflow.

### Telemetry (OpenTelemetry)

The service is instrumented with OpenTelemetry for distributed tracing and
structured JSON logging via `structlog`. Traces are shipped over OTLP/HTTP to
Grafana Cloud (or any OTLP-compatible backend) when
`OTEL_EXPORTER_OTLP_ENDPOINT` is set; otherwise they fall back to the console
exporter for local development.

Relevant env vars:

| Variable | Description |
|----------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/HTTP endpoint (e.g. Grafana Cloud tempo URL) |
| `OTEL_EXPORTER_OTLP_HEADERS` | `Authorization=Basic <base64>` header for the backend |
| `APP_ENV` | `prod` / `dev` — tagged on every span as `deployment.environment` |

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
