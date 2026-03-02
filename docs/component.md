# Component Definition

Every workspace component lives under `src/<component_name>/` and represents either an abstract contract implemented as an ABC or a concrete implementation.

## Directory Layout

```
<component_name>/
├── pyproject.toml
├── README.md
├── src/<component_name>/
│   ├── __init__.py
│   ├── client.py            # ABC definition (contract packages)
│   └── event.py             # event abstraction
└── tests/                   # component-scoped unit tests
```

## `pyproject.toml` Checklist

- `[project]`: align `name` with the folder, set `version`, `description`, `readme = "README.md"`, `requires-python = ">=3.11"`, and list direct dependencies.
- `[build-system]`: keep `hatchling` as the backend.
- `[tool.uv.sources]`: declare workspace dependencies when another component is required

## README Expectations

Document, at minimum: overview, scope, exposed interfaces, usage pattern, and component dependencies. Keep examples using absolute imports.

## Package Initialisation (`__init__.py`)

- **Contract packages** (`calendar_client_api`): export the ABCs (`Client`, `Event`), data models (`EventPatch`), and `get_*` factory hooks that raise `NotImplementedError` by default.
- **Implementation packages** (`outlook_client_impl`): import the contract, expose concrete classes and `get_*_impl` factories, and rebind the contract factories (e.g., `calendar_client_api.get_client = get_client_impl`). Registration runs at import time via `register()`.

## Testing

Component-level tests belong in `tests/`. Target the public interface, use mocks to isolate external services (e.g., mock `GraphServiceClient` for Outlook tests), and keep fixtures local to the component.
