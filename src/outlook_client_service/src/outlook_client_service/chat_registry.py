"""Helpers for loading a chat client implementation at runtime."""

from __future__ import annotations

import importlib
import os

from chat_client_api import ChatClient, get_client

CHAT_CLIENT_IMPL_MODULE_ENV = "CHAT_CLIENT_IMPL_MODULE"


def get_registered_chat_client() -> ChatClient:
    """Return the registered chat client, importing an env-configured implementation if needed."""
    try:
        return get_client()
    except RuntimeError as missing_client_error:
        module_name = os.getenv(CHAT_CLIENT_IMPL_MODULE_ENV)
        if not module_name:
            msg = (
                "No chat client implementation registered. Set "
                f"{CHAT_CLIENT_IMPL_MODULE_ENV} to an installed implementation module "
                "before using chat features."
            )
            raise RuntimeError(msg) from missing_client_error

        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            msg = f"Configured chat client implementation module '{module_name}' could not be imported."
            raise RuntimeError(msg) from exc

        return get_client()
