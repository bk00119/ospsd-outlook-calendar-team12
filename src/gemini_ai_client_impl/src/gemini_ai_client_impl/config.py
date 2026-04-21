

"""Configuration for Gemini AI client."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class GeminiConfig:
    """Configuration for Gemini client.

    Attributes:
        api_key: API key for Gemini.
        model: Model name to use.

    """

    api_key: str
    model: str = "gemini-1.5-flash"


def load_gemini_config() -> GeminiConfig:
    """Load Gemini configuration from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = "GEMINI_API_KEY is not set"
        raise ValueError(msg)

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    return GeminiConfig(api_key=api_key, model=model)
