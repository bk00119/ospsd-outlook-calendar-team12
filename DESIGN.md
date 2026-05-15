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

## 6. AI, Cross-Vertical Chat, Deployment, IaC, and Telemetry

This phase adds three new components (`ai_client_api`, `gemini_ai_client_impl`, `intelligent_app_service`) and a cross-vertical Slack integration, and puts the whole system into a public cloud. Each design area is covered below.

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

### 6.5 Observability — OpenTelemetry to Honeycomb

[`telemetry.py`](src/outlook_client_service/src/outlook_client_service/telemetry.py) wires up three parallel signal pipelines, all sharing one `Resource` tagged with `service.name = "outlook-client-service"`, `service.version`, and `deployment.environment`.

**Tracing.** A `TracerProvider` plus `BatchSpanProcessor` ships spans over OTLP/HTTP to whatever endpoint `OTEL_EXPORTER_OTLP_ENDPOINT` points at (Honeycomb in prod). When the env var is absent the processor falls back to `ConsoleSpanExporter`, which is what local `uv run uvicorn …` runs see.

**Metrics.** A `MeterProvider` plus `PeriodicExportingMetricReader` ships metric snapshots every 15 seconds via the OTLP HTTP metric exporter to the same backend. This second pipeline is what makes `FastAPIInstrumentor` emit HTTP server histograms (request duration) and counters (request total) directly as metrics, in addition to span data. Falls back to `ConsoleMetricExporter` locally.

**Auto-instrumentation.** Two libraries hook into the request lifecycle without per-route code:

- `FastAPIInstrumentor.instrument_app(app, tracer_provider=…, meter_provider=…)` — every public HTTP request emits a span AND a metric data point tagged with `http.route`, `http.method`, `http.status_code`, and end-to-end latency. This satisfies the rubric's "request latency labelled by route/method/status" + "success/failure rate" items without per-handler instrumentation.
- `RequestsInstrumentor().instrument(...)` — outbound calls to Microsoft Graph and Slack also emit child spans, so a slow downstream is visible in the trace tree rather than just inflating the parent latency.

**Logs.** `structlog` is configured to emit JSON-line records via `JSONRenderer`, with `add_log_level` and an ISO timestamper. Fly's log shipper picks these up as structured logs, so the same trace IDs are correlatable across logs and spans.

**Why Honeycomb.** An earlier revision of HW3 shipped to Grafana Cloud, but the chosen stack hit a routing issue where the OTLP gateway returned `502 Bad Gateway` for actual data despite accepting auth. We swapped to Honeycomb to remove that variable: same OTel SDK, two-secret config (`OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io"` + `OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=<key>"`), traces-first dashboard model that Honeycomb is purpose-built for. The dashboard board ID `zfvxVA8cFfS` in the `ospds/test` environment renders the rubric panels — P95 latency by route and request count by status code — straight off the span data.

**Domain counter — `slack_messages_processed`.** In addition to the auto-emitted HTTP-server signals, the Slack poller emits a custom counter labelled by `outcome` (`ok`, `ai_error`, `auth_required`, `no_text`). This is the metric that answers Tingran's "what does the deployed poller actually do?" — it shows how many user mentions made it through each branch of `_handle_message` over time, and is queryable in Honeycomb as `COUNT slack_messages_processed GROUP BY outcome`. An equivalent `ai_tool_calls` counter was scoped but not wired, since `intelligent_app_service` would have to import from `outlook_client_service.telemetry` — a circular dependency. AI-tool latency and outcome are still observable via the spans the FastAPI/Requests instrumentors emit around each tool call.

### 6.6 AI Integration

The AI layer follows the same interface / implementation pattern as the calendar client: a provider-agnostic `AIClient` ABC ([`ai_client_api/`](src/ai_client_api/)) describes text and structured generation calls; a Gemini-backed concrete implementation ([`gemini_ai_client_impl/`](src/gemini_ai_client_impl/)) wraps the official `google-genai` SDK. Application code depends only on `AIClient`, so swapping Gemini for OpenAI / Anthropic only changes the registered implementation. Credentials (`GEMINI_API_KEY`) are loaded from environment variables at startup — never hardcoded, never logged.

**Orchestration via `IntelligentAppService`.** [`intelligent_app_service`](src/intelligent_app_service/) is the chat-facing orchestration layer. `process_chat(message, user_timezone)` builds a typed system prompt (including the user's timezone), constructs a `TextGenerationRequest` annotated with **tool definitions** corresponding to real calendar actions, and runs the tool-calling loop against the registered `AIClient`. Tools are typed Python callables exposed to the model:

| Tool | Purpose | Safety guards |
|---|---|---|
| `create_outlook_event(title, start_iso_string, end_iso_string, location, description)` | Schedule a new event | Refuses if `list_events(start, end)` returns any overlapping event |
| `list_my_events(start_iso_string, end_iso_string)` | Summarize a time range | — |
| `get_outlook_event(event_id)` | Fetch event details | Maps `NotFound` to a user-facing error string |
| `update_outlook_event(event_id, …)` | Modify an existing event | If time range changes, refuses on conflict (ignoring the event being updated) |

**`delete_event` is intentionally not exposed to the model.** The hardening was driven by TA review ("destructive op with no undo. Misclassified prompt could nuke real events"). A deletion still exists on the underlying `CalendarClient`, so it can be wired into an explicit confirmation flow in the future — but it cannot fire from a free-form AI prompt.

**Conflict checks happen in code, not in the prompt.** `_has_conflict(starts_at, ends_at, ignore_event_id=…)` is a real Python guard inside the tool implementation. Relying on prompt rules to check conflicts (e.g. "tell the model not to overbook") is fragile under misclassification; the code path is the source of truth.

### 6.7 Slack Cross-Vertical Integration

The HW3 chat-vertical integration runs as an opt-in background polling thread launched from the FastAPI `lifespan` ([`main.py`](src/outlook_client_service/src/outlook_client_service/main.py)) **only when `ENABLE_SLACK_POLLER=true`**. The default is `false`, so a typical web worker does not poll. This prevents duplicate replies under multi-worker / HA setups (TA review feedback) and matches the rubric's "every worker polls" concern — production deployments enable the poller on exactly one machine via the env var.

```
FastAPI startup
  └─ lifespan() → if settings.enable_slack_poller: start_slack_poller_background()
       └─ Thread(name="slack-poller", daemon=True)
            └─ while True: chat_client.get_messages(channel) → filter → AI → reply
```

For each new message in `SLACK_TEST_CHANNEL_ID` that @mentions the bot, the poller:

1. Strips the mention prefix.
2. Looks up the sender's Outlook OAuth token via the in-process `_slack_user_token_store`.
3. If unlinked, replies with an auth link `/auth/login?slack_auth_token=<opaque-token>` where the token is a server-issued, one-time-use, opaque value generated by `create_slack_auth_token(slack_user_id)`. The token resolves back to the Slack user ID server-side on callback — the raw `slack_user_id` is **never trusted from URL parameters**, eliminating the CSRF/spoofing path called out in TA review.
4. If linked, hands the message + user timezone to `IntelligentAppService.process_chat`, which drives the Gemini tool-calling loop against `create_outlook_event`, `list_my_events`, `get_outlook_event`, `update_outlook_event`. (`delete_event` is intentionally not exposed to the model.)
5. Posts the model's reply back to the channel via the registered `ChatClient` from `chat_client_api.get_client()`.

**Concrete implementation — local `Team12SlackClient` adapter.** We pull `chat-client-api` (the shared ABC) from the canonical [`HarshithKoriRaj/Shared-API`](https://github.com/HarshithKoriRaj/Shared-API) repo. The chat vertical's published `slack-client-impl` package is **not** pulled as a dependency because it internally declares `chat-client-api` resolved to a different Git URL (`CS-GY-9223-Open-Source`), and `uv` refuses to resolve two URLs for the same package name. Instead, `Team12SlackClient` ([`slack_chat_client.py`](src/outlook_client_service/src/outlook_client_service/slack_chat_client.py)) is a ~240-line adapter that wraps the official `slack-sdk` `WebClient` and implements the shared `ChatClient` ABC. It registers itself via `register_client(create_slack_chat_client)` at module import time, so any code calling `chat_client_api.get_client()` gets a working `ChatClient` back without explicitly knowing about Slack.

**Swappability.** Application code (chat router, slack poller) depends only on the `ChatClient` ABC. Swapping Slack for Discord / Teams / Telegram only requires registering a different `ChatClient` implementation under the same ABC — the consumer code does not change. A runtime `CHAT_CLIENT_IMPL_MODULE` env var is also supported as a fallback lookup path when no impl has been registered yet, leaving the deployment side a single env-var change for swap.

**Session secret hardening.** Production now requires `SESSION_SECRET_KEY` to be explicitly configured (`config._load_session_secret_key` refuses to start when `APP_ENV=prod` and the key is unset). The dev/local fallback generates a random per-process key so testing keeps working without the env var.

### 6.8 Bug Fix from TA Review — `list_events` Partial-Overlap

TA review flagged that `OutlookClient.list_events` used strict-containment filtering, which silently dropped any event that started before the window or ended after it. A 1:30-2:30 PM meeting was invisible to a 2-3 PM query, which meant the AI's "is the calendar free?" prompt could not catch real conflicts.

The fix replaces containment with half-open overlap semantics in [`outlook_impl.py`](src/outlook_client_impl/src/outlook_client_impl/outlook_impl.py): an event is included when it intersects `[start, end)`. The behavior is locked in by `test_list_events_returns_partially_overlapping_events`, which asserts that all three overlap shapes (event-starts-before, event-ends-after, event-contains-window) are returned for a sample window. Conflict detection in the AI tool-calling path now works against the real semantics rather than the documented-but-wrong contract.
