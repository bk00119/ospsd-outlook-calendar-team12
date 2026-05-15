"""Abstract AI client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_client_api.models import (
        StructuredGenerationRequest,
        StructuredGenerationResponse,
        TextGenerationRequest,
        TextGenerationResponse,
    )


class AIClient(ABC):
    """Provider-agnostic AI client."""

    @abstractmethod
    def generate_text(
        self,
        request: TextGenerationRequest,
    ) -> TextGenerationResponse:
        """Generate text from a prompt."""

    @abstractmethod
    def generate_structured(
        self,
        request: StructuredGenerationRequest,
    ) -> StructuredGenerationResponse:
        """Generate structured output from a prompt."""
