"""Chat router — integrates AI orchestration with the shared chat vertical."""
from __future__ import annotations

from typing import Annotated

from chat_client_api import ChatClient
from chat_client_api import get_client as _get_chat_impl
from fastapi import APIRouter, Depends
from intelligent_app_service.service import (
    IntelligentAppService,  # noqa: TC002 — FastAPI evaluates Annotated type hints at runtime; moving to TYPE_CHECKING breaks dependency injection
)
from intelligent_app_service.wiring import (
    get_intelligent_app as get_intelligent_app,  # noqa: PLC0414 — explicit re-export required by mypy strict for test dependency overrides
)
from pydantic import BaseModel

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Incoming chat message payload."""

    message: str
    channel_id: str
    timezone: str = "UTC"


class ChatResponse(BaseModel):
    """AI-generated response to a chat message."""

    response: str


def get_chat_client() -> ChatClient:
    """Return the registered chat client (Slack implementation auto-registered on import)."""
    import slack_client_impl  # noqa: PLC0415 — registers SlackClient via DI pattern on import
    _ = slack_client_impl
    return _get_chat_impl()


def get_chat_intelligent_app() -> IntelligentAppService:
    """Return the default intelligent app service for the chat route."""
    return get_intelligent_app()


@router.post("/")
def chat(
    body: ChatRequest,
    service: Annotated[IntelligentAppService, Depends(get_chat_intelligent_app)],
    chat_client: Annotated[ChatClient, Depends(get_chat_client)],
) -> ChatResponse:
    """Process a natural language calendar command via AI and respond through chat.

    Receives a message from a chat channel, passes it to the AI orchestration
    service which interprets intent and performs calendar actions, then sends
    the response back to the originating channel via the chat client.
    """
    ai_response = service.process_chat(body.message, body.timezone)
    chat_client.send_message(channel_id=body.channel_id, text=ai_response)
    return ChatResponse(response=ai_response)
