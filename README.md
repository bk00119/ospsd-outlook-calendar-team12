# Team 12: Outlook (Calendar)

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

3.  **TODO: Instructions on setting up credentials**
    
    *Double check below workflow*

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

# TODO: Finish documentation after completing all requirements