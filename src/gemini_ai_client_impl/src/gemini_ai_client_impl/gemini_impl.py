"""Gemini implementation of AIClient."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, cast

from dotenv import load_dotenv
from google import genai
from google.genai import types

from ai_client_api import (
    AIClient,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    TextGenerationRequest,
    TextGenerationResponse,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from gemini_ai_client_impl.config import GeminiConfig

MAX_RETRY_TIME = 3


class GeminiAIClient(AIClient):
    """Gemini-based AI client implementation."""

    def __init__(self, config: GeminiConfig) -> None:
        """Initialize Gemini client with configuration."""
        self._config = config
        load_dotenv()

        api_key = config.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            msg = "GEMINI_API_KEY environment variable is not set."
            raise ValueError(msg)

        self._client = genai.Client(api_key=api_key)

    def generate_text(
        self,
        request: TextGenerationRequest,
    ) -> TextGenerationResponse:
        """Generate text from a prompt using Gemini (via Google SDK)."""
        tools = cast("list[types.Tool | Callable[..., Any]] | None", request.tools)

        system_instruction: str | None = None
        if request.context is not None:
            raw_system_instruction = request.context.get("system_instructions")
            if isinstance(raw_system_instruction, str) and raw_system_instruction.strip():
                system_instruction = raw_system_instruction.strip()

        content_config = types.GenerateContentConfig(
            tools=tools,
            max_output_tokens=request.max_tokens,
            system_instruction=system_instruction,
        )

        last_error: Exception | None = None
        for attempt in range(MAX_RETRY_TIME):
            try:
                response = self._client.models.generate_content(
                    model=self._config.model,
                    contents=request.prompt,
                    config=content_config,
                )
                return TextGenerationResponse(text=response.text or "")
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRY_TIME - 1:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                err_msg = (
                    "Gemini generate_content failed after 3 attempts "
                    f"for model '{self._config.model}': {exc!r}"
                )
                raise RuntimeError(err_msg) from exc

        err_msg = (
            "Gemini generate_content failed without returning a response. "
            f"Last error: {last_error!r}"
        )
        raise RuntimeError(err_msg)

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Generate structured output using Gemini."""
        raise NotImplementedError
