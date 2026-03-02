# Contributing to Outlook Calendar Client

This guide covers everything you need to get started, from setting up your environment to submitting a pull request.

## Prerequisites

- **Python 3.11** or higher
- **[uv](https://docs.astral.sh/uv/)** - Python package manager
  
## Development Setup

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd ospsd-outlook-calendar-team12
   ```

2. **Create and sync the virtual environment:**

   ```bash
   uv sync --all-packages --extra dev
   ```

   This installs all workspace packages and development tools (Ruff, MyPy, Pytest, MkDocs) into a `.venv` directory.

3. **Activate the virtual environment:**

   ```bash
   # macOS / Linux
   source .venv/bin/activate

   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

4. **Verify the installation:**

   ```bash
   ruff --version
   mypy --version
   pytest --version
   ```

## Workflow

1. Branch from `main` with a descriptive name (e.g. `yourname/feature-description`)
2. Keep your branch up to date by rebasing onto `main`:
3. Make your changes, ensure all tests pass
4. Push and open a PR. CircleCI will run checks

## Tooling

All code must pass linting and type checking before merging.

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check (strict mode)
uv run mypy src tests
```

## Running Tests

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

Coverage minimum is 85%.

## Pull Requests

- Run tests and checks locally before pushing
- Describe what the change does and how it was tested
- Fill out the PR template
- All CircleCI checks must pass
