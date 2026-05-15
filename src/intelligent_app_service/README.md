# Intelligent App Service

Application-level orchestration for the AI calendar assistant.

This component connects the provider-agnostic AI client to the calendar client
through dependency injection. It owns the domain actions exposed to the model as
tools.

## Dependencies

`IntelligentAppService` is constructed with:

- `calendar_client: calendar_client_api.Client`
- `ai_client: ai_client_api.AIClient`

The service does not construct provider SDK clients directly. Runtime wiring is
handled in `intelligent_app_service.wiring`, which currently builds the Gemini
AI client and the Outlook calendar client.

## Tool-Calling Flow

`process_chat(message, user_timezone)` builds a `TextGenerationRequest` with:

- the user's natural language message as `prompt`
- timezone-aware system instructions from `prompts.get_system_context()`
- calendar tool functions as `tools`

The tools map natural language requests into calendar actions:

- `create_outlook_event(...)` creates an Outlook event after checking for time
  conflicts in code
- `list_my_events(...)` lists events in a requested time window
- `get_outlook_event(...)` fetches details for one event
- `update_outlook_event(...)` updates an event and checks for time conflicts

The destructive delete operation is intentionally not exposed as an AI tool.
Deletion remains available only through normal calendar/service APIs.

## Calendar Action Results

Each tool returns a human-readable summary and records the latest tool result.
If the calendar action succeeds but the AI provider fails while generating the
final response, `process_chat()` returns a fallback message containing the
calendar result.

## Testing

Unit tests in `src/intelligent_app_service/tests/` use mocked calendar and AI
clients. They verify the tool list, calendar delegation, conflict checks,
fallback behavior, and that destructive delete is not exposed to the model.
