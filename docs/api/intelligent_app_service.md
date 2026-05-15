# Intelligent App Service

`intelligent_app_service` is the orchestration layer that drives the AI
tool-calling loop against calendar domain actions. `process_chat()` accepts a
natural-language message and a user timezone, exposes typed calendar tools
(`create_outlook_event`, `list_my_events`, `get_outlook_event`,
`update_outlook_event`) to the registered `AIClient`, and returns the model's
final reply. The destructive `delete_event` action is intentionally not
exposed to the model.

## Module: `service`

::: intelligent_app_service.service
    options:
      show_root_heading: true
      heading_level: 3

## Module: `models`

::: intelligent_app_service.models
    options:
      show_root_heading: true
      heading_level: 3

## Module: `prompts`

::: intelligent_app_service.prompts
    options:
      show_root_heading: true
      heading_level: 3

## Module: `wiring`

::: intelligent_app_service.wiring
    options:
      show_root_heading: true
      heading_level: 3

## Module: `exceptions`

::: intelligent_app_service.exceptions
    options:
      show_root_heading: true
      heading_level: 3
