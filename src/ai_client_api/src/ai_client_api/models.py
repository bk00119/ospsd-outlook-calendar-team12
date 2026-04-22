"""Data models for AI client requests and responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class TextGenerationRequest:
    """Request for generating a natural language response.

    Attributes:
        prompt: The main user prompt or instruction.
        context: Optional additional context to guide the model (e.g.,
            serialized events, issues, or metadata).
        max_tokens: Optional upper bound on response length.
        tools: Optional list of Python functions (tools) the AI can invoke.

    """

    prompt: str
    context: dict[str, Any] | None = None
    max_tokens: int | None = None
    tools: list[Callable[..., Any]] | None = None


@dataclass
class TextGenerationResponse:
    """Response containing generated natural language text.

    Attributes:
        text: The generated text output from the model.

    """

    text: str


@dataclass
class StructuredGenerationRequest:
    """Request for generating structured data.

    This is used when the caller expects the model to produce structured
    output (e.g., meeting draft, extracted fields) instead of free text.

    Attributes:
        prompt: The instruction describing what to generate.
        schema: A JSON-like schema describing the expected output shape.
        context: Optional additional context (e.g., issue data).

    """

    prompt: str
    schema: dict[str, Any]
    context: dict[str, Any] | None = None


@dataclass
class StructuredGenerationResponse:
    """Response containing structured output.

    Attributes:
        data: Parsed structured data returned by the model.

    """

    data: dict[str, Any]


@dataclass
class MeetingDraft:
    """Structured representation of a meeting draft.

    This is a convenience model for common use cases where the model
    generates a meeting title and description from issue data.

    Attributes:
        title: Suggested meeting title.
        description: Suggested meeting description.

    """

    title: str
    description: str


@dataclass
class ExtractedEvent:
    """Structured representation of an event draft extracted from natural language.

    This model represents AI-generated structured output before it has been
    validated and converted into a calendar domain model. Datetime values are
    stored as strings because LLM providers most naturally return structured
    text/JSON rather than Python ``datetime`` objects.

    Attributes:
        title: Event title.
        start_time: ISO-8601 datetime string with timezone information representing
            the start time.
        end_time: ISO-8601 datetime string with timezone information representing
            the end time.
        description: Optional event description.
        location: Optional event location.

    """

    title: str
    start_time: str
    end_time: str
    description: str | None = None
    location: str | None = None
