# Gemini AI Client Implementation

The `gemini_ai_client_impl` package is the Google Gemini implementation of the
`AIClient` ABC. It wraps the official `google-genai` SDK and registers itself
through the `get_client()` factory. Application code only depends on the
`AIClient` interface, so swapping Gemini for a different provider does not
require touching consumer code.

## Module: `gemini_impl`

::: gemini_ai_client_impl.gemini_impl
    options:
      show_root_heading: true
      heading_level: 3

## Module: `config`

::: gemini_ai_client_impl.config
    options:
      show_root_heading: true
      heading_level: 3
