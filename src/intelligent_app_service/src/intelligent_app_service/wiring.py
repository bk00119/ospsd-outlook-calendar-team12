"""Dependency wiring for intelligent app service."""
from ai_client_api import AIClient
from calendar_client_api import Client as CalendarClient
from intelligent_app_service.service import IntelligentAppService


def get_ai_client() -> AIClient:
    """Return the configured AI client implementation."""
    from gemini_ai_client_impl import GeminiAIClient, load_gemini_config  # noqa: PLC0415

    ai_config = load_gemini_config()
    return GeminiAIClient(ai_config)


def get_default_calendar_client() -> CalendarClient:
    """Return the registered default calendar client implementation."""
    import outlook_client_impl  # noqa: PLC0415
    from calendar_client_api import get_client as get_calendar_client  # noqa: PLC0415

    outlook_client_impl.register()
    return get_calendar_client()


def get_intelligent_app(
    calendar_client: CalendarClient | None = None,
) -> IntelligentAppService:
    """Wire dependencies and return the intelligent app service."""
    live_calendar = calendar_client or get_default_calendar_client()
    return IntelligentAppService(calendar_client=live_calendar, ai_client=get_ai_client())
