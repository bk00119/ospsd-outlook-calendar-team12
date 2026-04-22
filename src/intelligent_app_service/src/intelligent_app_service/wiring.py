"""Dependency wiring for intelligent app service."""

from intelligent_app_service.service import IntelligentAppService


def get_intelligent_app() -> IntelligentAppService:
    """Wire dependencies and return the live robust Application Orchestrator."""
    # 1. Start AI Client natively
    from gemini_ai_client_impl import GeminiAIClient, load_gemini_config  # noqa: PLC0415
    ai_config = load_gemini_config()
    ai_client = GeminiAIClient(ai_config)

    # 2. Start Real Outlook Calendar Client
    import outlook_client_impl  # noqa: PLC0415
    outlook_client_impl.register()
    from calendar_client_api import get_client as get_calendar_client  # noqa: PLC0415

    # fetch the exact live network Outlook client that already has OAuth tokens.
    live_calendar = get_calendar_client()

    # 3. Wire them together into the App
    return IntelligentAppService(calendar_client=live_calendar, ai_client=ai_client)
