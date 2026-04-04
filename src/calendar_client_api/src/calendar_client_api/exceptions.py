"""Domain exceptions exposed by the calendar client API."""


class CalendarError(Exception):
    """Base exception for calendar-domain errors."""


class CalendarValidationError(CalendarError):
    """Raised when input or request payload is invalid."""


class CalendarNotFoundError(CalendarError):
    """Raised when a requested calendar resource does not exist."""


class CalendarAuthError(CalendarError):
    """Raised when authentication or authorization fails."""


class CalendarServiceError(CalendarError):
    """Raised when service/provider communication fails."""
