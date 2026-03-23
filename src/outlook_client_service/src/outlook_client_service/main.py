"""FastAPI application entrypoint for the Outlook client service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from outlook_client_service.config import settings
from outlook_client_service.routers import auth, events, health


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Include routers ---
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(events.router, prefix="/events", tags=["events"])

    return app


# FastAPI entrypoint
app = create_app()
