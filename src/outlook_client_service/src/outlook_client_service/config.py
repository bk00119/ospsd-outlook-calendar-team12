"""Configuration settings for the Outlook client service."""

import os
import secrets
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _load_session_secret_key() -> str:
    """Load the session signing key without falling back to a hardcoded value."""
    configured_secret = os.getenv("SESSION_SECRET_KEY")
    if configured_secret:
        return configured_secret

    environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
    if environment in {"prod", "production"}:
        msg = "SESSION_SECRET_KEY must be configured in production."
        raise RuntimeError(msg)

    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = "Outlook Client Service"
    app_description: str = "FastAPI service wrapping Outlook client implementation"
    app_version: str = "0.1.0"

    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")

    azure_client_id: str = os.getenv("AZURE_CLIENT_ID", "")
    azure_client_secret: str = os.getenv("AZURE_CLIENT_SECRET", "")
    azure_login_uri: str = os.getenv(
        "AZURE_LOGIN_URI",
        "http://localhost:8000/auth/login",
    )
    azure_redirect_uri: str = os.getenv(
        "AZURE_REDIRECT_URI",
        "http://localhost:8000/auth/callback",
    )
    azure_authority: str = os.getenv("AZURE_AUTHORITY", "https://login.microsoftonline.com/consumers")

    session_secret_key: str = _load_session_secret_key()

    cors_origins_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:8000")

    def cors_origins(self) -> list[str]:
        """Return parsed CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    enable_slack_poller: bool = os.getenv("ENABLE_SLACK_POLLER", "false").lower() == "true"

    calendar_provider: str = os.getenv("CALENDAR_PROVIDER", "outlook").strip().lower()
    google_credentials_file: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    google_token_file: str = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    google_calendar_id: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    google_interactive_auth: bool = (
            os.getenv("GOOGLE_INTERACTIVE_AUTH", "false").lower() == "true"
    )


settings = Settings()
