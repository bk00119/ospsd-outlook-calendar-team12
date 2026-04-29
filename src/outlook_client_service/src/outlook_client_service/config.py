"""Configuration settings for the Outlook client service."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


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

    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "dev-secret-key")

    cors_origins_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:8000")

    def cors_origins(self) -> list[str]:
        """Return parsed CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
