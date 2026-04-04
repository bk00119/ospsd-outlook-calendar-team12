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

    # Run end to end tests
    uv run pytest -m e2e

    # With coverage report
    uv run pytest --cov=src --cov-report=term-missing
    ```

- **Documentation (MkDocs):**
    ```bash
    uv run mkdocs serve
    ```
    Open your browser to `http://127.0.0.1:8000` to view the site.

## Continuous Integration

The project uses CircleCI (`.circleci/config.yml`) with two workflows:

- **All Branches**: Build, lint, unit tests, and CI-compatible integration tests
- **Main/Develop**: Additional integration tests with real Microsoft Graph API calls using credentials from the `outlook-client` CircleCI context
