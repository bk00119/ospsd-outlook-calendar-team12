"""FastAPI application entrypoint for the Outlook client service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from outlook_client_service.config import settings
from outlook_client_service.routers import auth, events, health
from outlook_client_service.telemetry import configure_telemetry


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
        allow_origins=settings.cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # --- Include routers ---
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(events.router, prefix="/events", tags=["events"])

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """Redirect root to the login page."""
        return RedirectResponse(url="/auth/login")

    configure_telemetry(app)

    return app


# FastAPI entrypoint
app = create_app()
