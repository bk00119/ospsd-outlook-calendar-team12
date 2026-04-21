"""AI client exceptions."""


class AIClientError(Exception):
    """Base AI client error."""


class AIRequestError(AIClientError):
    """Raised when an AI request fails."""


class AIResponseParseError(AIClientError):
    """Raised when an AI response cannot be parsed."""
