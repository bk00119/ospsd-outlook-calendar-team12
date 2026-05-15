# AI Client API

Provider-agnostic interface for AI text generation.

This component defines the contract that application code uses. It does not
import Gemini, OpenAI, Anthropic, HTTP clients, credentials, or provider SDK
types. Implementations live in separate packages such as
`gemini_ai_client_impl`.

## Interface

`AIClient` exposes two methods:

- `generate_text(request: TextGenerationRequest) -> TextGenerationResponse`
- `generate_structured(request: StructuredGenerationRequest) -> StructuredGenerationResponse`

`TextGenerationRequest` contains:

- `prompt`: the user message or task instruction
- `context`: optional provider-agnostic metadata, such as system instructions
- `max_tokens`: optional output limit
- `tools`: optional Python callables that an implementation may expose to the
  model as function-calling tools

## Tool Calling Contract

Tools are plain Python callables passed through `TextGenerationRequest.tools`.
The API package only models the shape of the request; it does not execute tools
itself. The provider implementation is responsible for giving the tools to the
model, while the application service owns the domain logic behind those tools.

For this project, `intelligent_app_service` passes calendar functions such as
creating, listing, retrieving, and updating Outlook events. The AI provider can
invoke those functions through tool calling, but the calendar client remains
behind the application service boundary.

## Structured Generation

The interface includes `generate_structured()` for future provider support.
The current Gemini implementation intentionally does not support structured
generation for HW3 and raises `NotImplementedError`.
