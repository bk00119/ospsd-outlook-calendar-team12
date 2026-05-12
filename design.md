# Design Document

This document explains the system design for the Outlook Calendar Client project across both homework phases. HW1 established the local interface and provider implementation. HW2 extends that design into a deployable service while preserving the same client-facing contract.

## 1. Architecture Overview

### HW1 Foundation

HW1 introduced the core separation between contract and implementation:

- `calendar_client_api`: defines the abstract `Client` and `Event` interfaces plus `EventPatch`. This package is provider-agnostic and contains no Microsoft Graph or HTTP-specific logic.
- `outlook_client_impl`: provides `OutlookClient`, a concrete implementation of the `Client` contract backed by Microsoft Graph. It also contains authentication support and event parsing logic.

This separation keeps consumer code dependent on a stable calendar interface rather than on Outlook-specific SDK details.

### HW2 Additions

HW2 keeps the HW1 packages and adds three new layers:

- `outlook_client_service`: a FastAPI service that exposes the calendar operations over HTTP. It also provides OAuth routes and a `/health` endpoint.
- `outlook_client_service_api_client`: an auto-generated Python client created from the FastAPI OpenAPI schema. This package handles typed request and response models for the service.
- `outlook_service_client_adapter`: an adapter that implements the original `calendar_client_api.Client` contract by delegating to the generated HTTP client.

### Resulting System

The full workspace has five packages:

1. `calendar_client_api`
2. `outlook_client_impl`
3. `outlook_client_service`
4. `outlook_client_service_api_client`
5. `outlook_service_client_adapter`

The design goal is location transparency. A caller can program against `calendar_client_api.Client` and use either:

- the local implementation from HW1: `OutlookClient`
- the remote service path from HW2: `ServiceClientAdapter`

without changing the rest of the application logic.

## 2. Request Flow

### HW1 Local Flow

In the original local design, consumer code calls a method on `calendar_client_api.Client`, and the concrete `OutlookClient` implementation directly talks to Microsoft Graph. The flow is:

`consumer -> Client ABC -> OutlookClient -> Microsoft Graph -> OutlookClient -> Event`

This path is simple and efficient, but it requires the Outlook implementation and Graph access to exist in the same runtime as the caller.

### HW2 Remote Flow

HW2 inserts a service boundary while keeping the same abstract interface. A `get_event` call flows through the system as follows:

1. Consumer code calls `get_event(event_id)` on an object typed as `calendar_client_api.Client`.
2. The concrete instance is `ServiceClientAdapter`, not `OutlookClient`.
3. `ServiceClientAdapter.get_event(...)` calls the generated client function for `GET /events/{event_id}`.
4. The generated client sends an HTTP request to `outlook_client_service`.
5. The FastAPI route receives the request and resolves an authenticated `OutlookClient`.
6. `OutlookClient.get_event(...)` retrieves the event from Microsoft Graph.
7. The service converts the returned `Event` into an `EventResponse` schema.
8. The generated client parses the JSON response into typed Python models.
9. The adapter maps the generated model back into an object implementing the original `Event` contract.

This path preserves the same caller-facing API while moving the implementation behind a network boundary.

### Sample API Response

A `GET /events/{event_id}` request returns:

```json
{
  "id": "AAMkAGQ2...",
  "title": "Team Standup",
  "starts_at": "2026-04-03T14:00:00+00:00",
  "ends_at": "2026-04-03T15:00:00+00:00",
  "location": "Room 101",
  "description": "Weekly sync"
}
```

### Authentication in the Flow

HW2 also changes authentication responsibilities. In HW1, authentication was primarily local to the implementation. In HW2, the service owns the OAuth 2.0 web flow:

- `/auth/login` redirects the user to Microsoft
- `/auth/callback` exchanges the authorization code for tokens
- session state stores access and refresh token data
- event routes depend on the current authenticated session

This is necessary because the deployed service must authenticate web users rather than rely on a purely local developer flow.

## 3. API Design With Error Handling

### Stable Contract at the Boundary

The main API exposed to application code remains the `calendar_client_api.Client` interface:

- `get_event`
- `list_events`
- `create_event`
- `update_event`
- `delete_event`

That contract does not expose HTTP transport details, FastAPI types, or Microsoft Graph SDK models.

### Service Layer

The FastAPI service exposes HTTP endpoints for the core calendar operations plus authentication and health checks. Its responsibilities are:

- validate request data using FastAPI and schema models
- translate HTTP requests into calls on `OutlookClient`
- translate returned events into JSON response schemas
- expose operational endpoints such as `/health`

When the implementation raises an exception, the service wraps that failure as an HTTP error response instead of leaking internal exceptions directly to the client.

### Endpoints

| Method | Path | Request Body | Response | Status |
|--------|------|-------------|----------|--------|
| GET | `/events/` | — | `EventResponse[]` | 200 |
| POST | `/events/` | `EventCreateRequest` | `EventResponse` | 201 |
| GET | `/events/{event_id}` | — | `EventResponse` | 200 |
| PATCH | `/events/{event_id}` | `EventUpdateRequest` | `EventResponse` | 200 |
| DELETE | `/events/{event_id}` | — | — | 204 |
| GET | `/auth/login` | — | Redirect to Microsoft | 302 |
| GET | `/auth/callback` | — | Session cookie set | 200 |
| POST | `/auth/logout` | — | Session cleared | 200 |
| GET | `/health` | — | `{"status": "ok"}` | 200 |

### Generated Client Layer

The auto-generated client is intentionally thin. It knows:

- endpoint paths and HTTP methods
- request and response schemas
- documented status-code-specific response models

For example, the generated `get_event` client parses:

- `200` into `EventResponse`
- `422` into `HTTPValidationError`

and may return `None` for undocumented responses when unexpected statuses are not configured to raise.

### Adapter Error Translation

The adapter exists to prevent HTTP-specific behavior from leaking into application code. It translates generated-client outputs into normal Python behavior:

- successful responses are mapped into objects implementing the `Event` contract
- validation responses become `CalendarValidationError`
- missing or unusable payloads become `CalendarServiceError`
- HTTP 404 responses become `CalendarNotFoundError`
- authentication failures become `CalendarAuthError`
- transport exceptions from the generated client are translated via `_raise_mapped_http_error`

These domain exceptions are defined in `calendar_client_api.exceptions`, keeping error handling consistent whether using the local implementation or the remote adapter.

## 4. Adapter Pattern Rationale With Code Comparison

The adapter pattern is used to preserve the original HW1 interface while adding a remote deployment model in HW2.

Without the adapter, client code would need to know whether it was calling:

- a local Python implementation, or
- a generated HTTP client with service-specific models

That would couple application code to deployment details. The adapter removes that coupling.

### Direct Local Usage

```python
from outlook_client_impl.outlook_impl import OutlookClient

client = OutlookClient(interactive=False)
event = client.get_event(event_id)
```

### Remote Service Usage Through the Adapter

```python
from outlook_client_service_api_client.client import Client as GeneratedClient
from outlook_service_client_adapter.adapter import ServiceClientAdapter

generated = GeneratedClient(base_url="http://localhost:8000")
client = ServiceClientAdapter(generated)
event = client.get_event(event_id)
```

The important design point is that both objects satisfy the same abstract interface. Consumer code can be written against `calendar_client_api.Client` and remain unchanged while the backing implementation changes from local to remote.

This is the central architectural improvement in HW2.

## 5. Testing Strategy

Testing is split by layer so failures are easier to isolate and reason about.

| Layer                     | Location                                    | Purpose                                                                                  |
| ------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------- |
| API contract              | `src/calendar_client_api/tests/`            | Verifies the abstract client and event contracts expected by consumers                   |
| Implementation unit tests | `src/outlook_client_impl/tests/`            | Verifies `OutlookClient` behavior with mocked Graph service interactions                 |
| Service tests             | `src/outlook_client_service/tests/`         | Verifies route behavior, schema mapping, HTTP error translation, and OAuth route logic   |
| Adapter tests             | `src/outlook_service_client_adapter/tests/` | Verifies delegation to the generated client, response mapping, and exception translation |
| Integration and E2E       | `tests/integration/`, `tests/e2e/`          | Verifies larger multi-component flows where present                                      |

### Why the Layers Are Tested Separately

- API tests protect the core contract from accidental interface drift.
- Implementation tests confirm Microsoft Graph interactions without requiring the full service stack.
- Service tests verify that HTTP routes correctly call the implementation and return the right schema and status behavior.
- Adapter tests verify that the remote client path still behaves like the original local contract.

This layered strategy is especially important in HW2 because the system now contains multiple translation boundaries:

- Graph model to domain event
- domain event to FastAPI response schema
- HTTP JSON to generated client model
- generated client model to `Event` contract through the adapter

Testing each boundary independently makes it easier to identify where a regression occurred.

### Mocking Strategy

- **Unit tests** mock external boundaries. Adapter tests patch the generated client module functions (`delete_event_events_event_id_delete.sync`, etc.) so no HTTP calls are made. Implementation tests mock `GraphServiceClient` to avoid real Microsoft Graph calls. Service tests use FastAPI's `TestClient` with a mocked `OutlookClient` injected via `Depends` override.
- **Integration tests** use `httpx.MockTransport` to simulate real HTTP responses without a running server. This verifies the full adapter → generated client → HTTP path with controlled responses, testing serialization and deserialization across the boundary.
- **E2E tests** run against the real Microsoft Graph API with no mocks, gated behind environment variables (`E2E=1`) and disabled by default.

### Interface Compliance

The adapter is verified as a correct implementation of the `Client` ABC through two mechanisms:

1. **Static type checking**: `mypy --strict` verifies that `ServiceClientAdapter` implements all abstract methods with compatible signatures. Any missing or mistyped method is caught at analysis time.
2. **Integration tests**: The DI wiring test imports the adapter package, which triggers `register()`, then asserts that `calendar_client_api.get_client()` returns a `ServiceClientAdapter` instance. Adapter unit tests verify that each method delegates correctly and maps responses into `Event`-compatible objects.

## 6. HW3: Deployment, IaC, and Telemetry

HW3 adds three new components (`ai_client_api`, `gemini_ai_client_impl`, `intelligent_app_service`) and a cross-vertical Slack integration, and puts the whole system into a public cloud. The deployment-layer design decisions are below.

### 6.1 Hosting Choice — Fly.io

The service is deployed to [Fly.io](https://fly.io) as a single container running the FastAPI app defined in `outlook_client_service`. Fly was chosen over AWS/GCP/Render for three reasons:

- **One config file, one CLI** — `fly.toml` + `flyctl deploy` covers the whole deploy path, which keeps the IaC surface small for a five-person student project.
- **Free tier + auto-stop** — `min_machines_running = 0` plus `auto_start_machines = true` lets the machine sleep when idle and wake on the first request. This matches the rubric's "shut it down after recording the video" guidance directly.
- **No proxy/LB to manage** — Fly's edge handles TLS termination and HTTPS redirect (`force_https = true`), so the FastAPI app only needs to listen on `:8000` inside the container.

The container image is a multi-stage Python 3.12-slim Dockerfile that copies the locked `uv` workspace, syncs `--no-dev`, and exposes `:8000` running `uvicorn`.

### 6.2 Infrastructure as Code — fly.toml as Single Source of Truth

An earlier revision of HW3 had **both** a `terraform/` directory (using the `fly-apps/fly` provider) and a `fly.toml` describing the same Fly.io app. The two files disagreed on the machine, image, and HTTPS settings, and CI only ever used `fly.toml`, so the Terraform side was effectively unused. TA review flagged this as a "pick one source of truth" issue.

The team chose to **drop Terraform and treat `fly.toml` as the IaC artifact**. Rationale:

- `fly.toml` is fully declarative: it pins `app`, `primary_region`, VM `cpu_kind`/`cpus`/`memory_mb`, port mapping (`internal_port = 8000`), HTTPS policy, healthcheck (`GET /health` every 30s), and the auto-stop policy. From a clean state, `flyctl deploy --config fly.toml` produces the deployed environment.
- The Terraform stack was duplicating the same information without adding lifecycle, drift detection, or multi-environment parameterization that the team actually used.
- Keeping a single source removes the documented divergence and matches what CI actually runs.

**Tradeoff accepted**: the rubric's IaC entry names "Terraform / CloudFormation / Pulumi / CDK" explicitly. We are betting that `fly.toml`'s declarative, repeatable, version-controlled, fully-IaC behavior reads as IaC for the grader; if not, a thin Pulumi/CDK stack that renders `fly.toml` is the planned fallback.

### 6.3 Secrets Management

No provider credentials live in source. Three layers:

| Layer | Storage | Examples |
|-------|---------|----------|
| Local dev | `.env` (git-ignored) | `AZURE_CLIENT_ID`, `GEMINI_API_KEY`, `SLACK_BOT_TOKEN` |
| Fly.io runtime | `fly secrets set KEY=value` → Fly's encrypted secrets store | Same keys as `.env`, plus `OTEL_EXPORTER_OTLP_HEADERS` (contains the Grafana Cloud token) |
| CI | CircleCI project-level env vars + the `outlook-client` context | `FLY_API_TOKEN`, Azure credentials for the optional real-Graph integration tests |

Neither the Dockerfile nor `fly.toml` ever sees a secret value — they only see the names. Secrets are injected by the platform at process-start time.

### 6.4 CI/CD Deploy Pipeline

[`.circleci/config.yml`](.circleci/config.yml) defines a single `deploy` job that runs after `lint` and `circleci_test`:

1. Install `flyctl` on a `cimg/base:stable` runner.
2. Require `FLY_API_TOKEN` to be present in the CircleCI env (the job exits non-zero if not).
3. Run `flyctl deploy --remote-only --config fly.toml`. `--remote-only` tells Fly to build the Docker image on Fly's builders rather than in CircleCI, which avoids shipping a Docker daemon to the runner.

The job is filtered to `hw-3` and the `jaik/hw3-deployment-telemetry` working branch, so feature branches run the test suite but never push a deploy. After HW3 merges to `main`, the `full_integration` workflow takes over and also deploys.

### 6.5 Observability — OpenTelemetry to Grafana Cloud

[`telemetry.py`](src/outlook_client_service/src/outlook_client_service/telemetry.py) wires up two parallel signal pipelines:

**Tracing.** A `TracerProvider` is built with a `Resource` tagged `service.name = "outlook-client-service"`, `service.version`, and `deployment.environment`. A `BatchSpanProcessor` ships spans over OTLP/HTTP to whatever endpoint `OTEL_EXPORTER_OTLP_ENDPOINT` points at (Grafana Cloud Tempo in prod). When the env var is absent the processor falls back to `ConsoleSpanExporter`, which is what local `uv run uvicorn …` runs see.

**Auto-instrumentation.** Two libraries hook into the request lifecycle without per-route code:

- `FastAPIInstrumentor.instrument_app(app)` — every public HTTP request emits a span tagged with `http.route`, `http.method`, `http.status_code`, and end-to-end latency. This satisfies the rubric's "request latency labelled by route/method/status" + "success/failure rate" items without per-handler instrumentation.
- `RequestsInstrumentor().instrument()` — outbound calls to Microsoft Graph and Slack also emit child spans, so a slow downstream is visible in the trace tree rather than just inflating the parent latency.

**Logs.** `structlog` is configured to emit JSON-line records via `JSONRenderer`, with `add_log_level` and an ISO timestamper. Fly's log shipper picks these up as structured logs, so the same trace IDs are correlatable across logs and spans.

### 6.6 Slack Cross-Vertical Integration

The HW3 chat-vertical integration runs as a background polling thread launched from the FastAPI `lifespan` ([`main.py`](src/outlook_client_service/src/outlook_client_service/main.py)):

```
FastAPI startup
  └─ lifespan() → start_slack_poller_background()
       └─ Thread(name="slack-poller", daemon=True)
            └─ while True: chat_client.get_messages(channel) → filter → AI → reply
```

For each new message in `SLACK_TEST_CHANNEL_ID` that @mentions the bot, the poller:

1. Strips the mention prefix.
2. Looks up the sender's Outlook OAuth token via `get_calendar_client_for_slack_user(slack_user_id)`.
3. If unlinked, replies with an auth link (`/auth/login?slack_user_id=…`) that binds the Outlook session to the Slack user on callback.
4. If linked, hands the message + user timezone to `IntelligentAppService.process_chat`, which drives the Gemini tool-calling loop against `create_outlook_event`, `list_my_events`, etc.
5. Posts the model's reply back to the channel via the shared `chat_client_api`.

The chat client is resolved through the cross-vertical `chat_client_api.get_client()` factory — `slack_client_impl` is imported solely to trigger its `register()` side-effect, mirroring the HW1 DI pattern. Swapping Slack out for a different chat provider (e.g. Discord) only requires registering a different implementation under the same ABC.

**Known caveats** (called out in TA review, deferred for the final sprint):

- The Slack user → Outlook token mapping is held in an in-memory dict and is lost on process restart. A persistent store is the next iteration.
- Auto-starting the poller from `lifespan` means every Fly machine in an HA fleet would poll the same channel. The standalone `run_slack_poller.py` entry point exists as the production deployment path; today's single-machine Fly setup makes this a non-issue but it will need an env flag before HA.

### 6.7 Bug Fix from TA Review — `list_events` Partial-Overlap

TA review flagged that `OutlookClient.list_events` used strict-containment filtering, which silently dropped any event that started before the window or ended after it. A 1:30-2:30 PM meeting was invisible to a 2-3 PM query, which meant the AI's "is the calendar free?" prompt could not catch real conflicts.

The fix replaces containment with half-open overlap semantics in [`outlook_impl.py`](src/outlook_client_impl/src/outlook_client_impl/outlook_impl.py): an event is included when it intersects `[start, end)`. The behavior is locked in by `test_list_events_returns_partially_overlapping_events`, which asserts that all three overlap shapes (event-starts-before, event-ends-after, event-contains-window) are returned for a sample window. Conflict detection in the AI tool-calling path now works against the real semantics rather than the documented-but-wrong contract.
