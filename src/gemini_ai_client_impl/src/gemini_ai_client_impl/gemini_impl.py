

"""Gemini implementation of AIClient."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        # TODO: Initialize Gemini SDK client here

    def generate_text(
        self,
        request: TextGenerationRequest,
    ) -> TextGenerationResponse:
        """Generate text from a prompt using Gemini."""
        # TODO: Call Gemini API and return response
        raise NotImplementedError

    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Generate structured output using Gemini."""
        # TODO: Call Gemini API and parse structured output
        raise NotImplementedError
