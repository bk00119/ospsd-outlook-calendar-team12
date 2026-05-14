"""Unit tests for the Gemini AI client implementation."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, call

import gemini_ai_client_impl.gemini_impl as gemini_module
import pytest
from google.genai import types

from ai_client_api import StructuredGenerationRequest, TextGenerationRequest
from gemini_ai_client_impl import GeminiAIClient, GeminiConfig

pytestmark = pytest.mark.unit

MAX_TEST_TOKENS = 128
EXPECTED_RETRY_CALLS = 2


@dataclass
class _Response:
    """Small stand-in for a Google GenAI response object."""

    text: str | None


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    generate_content: MagicMock,
    *,
    api_key: str = "test-api-key",
    model: str = "models/gemini-test",
) -> tuple[GeminiAIClient, MagicMock]:
    """Create a GeminiAIClient with a mocked Google SDK client."""
    fake_models = MagicMock()
    fake_models.generate_content = generate_content
    fake_google_client = MagicMock()
    fake_google_client.models = fake_models
    client_factory = MagicMock(return_value=fake_google_client)
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.genai.Client", client_factory)
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.load_dotenv", MagicMock())

    return GeminiAIClient(GeminiConfig(api_key=api_key, model=model)), client_factory


def test_init_loads_gemini_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load GEMINI_API_KEY from the environment when config has no key."""
    client_factory = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.genai.Client", client_factory)
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.load_dotenv", MagicMock())
    monkeypatch.setenv("GEMINI_API_KEY", "env-api-key")

    GeminiAIClient(GeminiConfig(api_key="", model="models/gemini-test"))

    client_factory.assert_called_once_with(api_key="env-api-key")


def test_init_rejects_missing_gemini_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail clearly when no Gemini API key is configured."""
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.load_dotenv", MagicMock())
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiAIClient(GeminiConfig(api_key="", model="models/gemini-test"))


def test_generate_text_passes_prompt_model_system_instruction_and_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass request details through to models.generate_content."""

    def create_event(title: str) -> str:
        """Fake tool used to verify tool forwarding."""
        return f"Created {title}"

    generate_content = MagicMock(return_value=_Response(text="Calendar action complete."))
    client, _ = _make_client(monkeypatch, generate_content)

    response = client.generate_text(
        TextGenerationRequest(
            prompt="Schedule a review tomorrow at 2pm.",
            context={"system_instructions": " Use calendar tools only when needed. "},
            max_tokens=MAX_TEST_TOKENS,
            tools=[create_event],
        ),
    )

    assert response.text == "Calendar action complete."
    generate_content.assert_called_once()
    call_kwargs = generate_content.call_args.kwargs
    assert call_kwargs["model"] == "models/gemini-test"
    assert call_kwargs["contents"] == "Schedule a review tomorrow at 2pm."
    content_config = call_kwargs["config"]
    assert isinstance(content_config, types.GenerateContentConfig)
    assert content_config.system_instruction == "Use calendar tools only when needed."
    assert content_config.max_output_tokens == MAX_TEST_TOKENS
    assert content_config.tools == [create_event]


def test_generate_text_retries_transient_google_sdk_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry transient Google SDK failures before returning a response."""
    generate_content = MagicMock(
        side_effect=[
            RuntimeError("temporary outage"),
            _Response(text="Recovered response."),
        ],
    )
    sleep = MagicMock()
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.time.sleep", sleep)
    client, _ = _make_client(monkeypatch, generate_content)

    response = client.generate_text(TextGenerationRequest(prompt="List tomorrow events."))

    assert response.text == "Recovered response."
    assert generate_content.call_count == EXPECTED_RETRY_CALLS
    sleep.assert_called_once_with(1.0)


def test_generate_text_raises_after_retry_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise RuntimeError after all Gemini retry attempts fail."""
    generate_content = MagicMock(side_effect=RuntimeError("provider unavailable"))
    sleep = MagicMock()
    monkeypatch.setattr("gemini_ai_client_impl.gemini_impl.time.sleep", sleep)
    client, _ = _make_client(monkeypatch, generate_content)

    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        client.generate_text(TextGenerationRequest(prompt="Create event."))

    assert generate_content.call_count == gemini_module.MAX_RETRY_TIME
    assert sleep.call_args_list == [call(1.0), call(2.0)]


def test_generate_structured_is_intentionally_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Document current HW3 behavior for structured generation."""
    client, _ = _make_client(
        monkeypatch,
        MagicMock(return_value=_Response(text="unused")),
    )

    with pytest.raises(NotImplementedError):
        client.generate_structured(
            StructuredGenerationRequest(
                prompt="Extract a calendar event.",
                schema={"type": "object"},
            ),
        )
