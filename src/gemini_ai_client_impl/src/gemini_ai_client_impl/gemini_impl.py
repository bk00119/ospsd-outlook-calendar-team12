"""Gemini implementation of AIClient."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

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
    from gemini_ai_client_impl.config import GeminiConfig


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
        config_kwargs = {}
        if request.tools:
            config_kwargs["tools"] = request.tools
        if request.max_tokens:
            config_kwargs["max_output_tokens"] = request.max_tokens

        content_config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        prompt = request.prompt
        if request.context:
            prompt = f"System Context:\n{request.context}\n\nUser Task:\n{prompt}"

        response = self._client.models.generate_content(
            model=self._config.model,
            contents=prompt,
            config=content_config,
        )

        return TextGenerationResponse(text=response.text or "")

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Generate structured output using Gemini."""
        raise NotImplementedError
