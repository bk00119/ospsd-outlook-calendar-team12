# Gemini AI Client Implementation

Concrete `AIClient` implementation backed by the Google GenAI SDK.

Consumers should depend on `ai_client_api.AIClient`; this package is the
provider-specific implementation that wires that interface to Gemini.

## Configuration

The implementation uses `GeminiConfig`:

- `api_key`: Gemini API key. If this is empty, `GeminiAIClient` falls back to
  the `GEMINI_API_KEY` environment variable after loading `.env`.
- `model`: Gemini model name. The default from `load_gemini_config()` is
  `models/gemma-4-31b-it`, or `GEMINI_MODEL` if set.

No API key is hardcoded in source control.

## Text Generation

`generate_text()` converts `TextGenerationRequest` into a Google
`GenerateContentConfig` and calls:

```python
self._client.models.generate_content(
    model=self._config.model,
    contents=request.prompt,
    config=content_config,
)
```

The config forwards:

- `request.tools` as Gemini tools
- `request.max_tokens` as `max_output_tokens`
- `request.context["system_instructions"]` as `system_instruction` when present

The method returns `TextGenerationResponse(text=response.text or "")`.

## Retry Behavior

Gemini calls are retried up to three attempts. Between failed attempts the
implementation sleeps with a short linear backoff. If all attempts fail,
`generate_text()` raises `RuntimeError` with the model name and final provider
error included.

## Structured Generation

`generate_structured()` is intentionally unsupported for HW3 and raises
`NotImplementedError`. The current intelligent calendar flow uses native tool
calling instead of provider-specific structured output.

## Tests

Unit tests live under `src/gemini_ai_client_impl/tests/`. They mock
`genai.Client` and `models.generate_content`, so they do not call the real
Gemini API or require a real `GEMINI_API_KEY`.
