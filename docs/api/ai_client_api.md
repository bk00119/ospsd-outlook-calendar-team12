# AI Client API

The `ai_client_api` package defines the provider-agnostic abstract interface
for AI clients used by `intelligent_app_service` and any other component that
needs language-model orchestration. Concrete implementations (e.g.
`gemini_ai_client_impl`) inherit from `AIClient` and register themselves via
the `get_client()` factory.

## Module: `client`

::: ai_client_api.client
    options:
      show_root_heading: true
      heading_level: 3

## Module: `models`

::: ai_client_api.models
    options:
      show_root_heading: true
      heading_level: 3

## Module: `exceptions`

::: ai_client_api.exceptions
    options:
      show_root_heading: true
      heading_level: 3
