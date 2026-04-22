"""Adapter that wraps the auto-generated service client with the Client ABC."""

from outlook_service_client_adapter.adapter import ServiceClientAdapter
from outlook_service_client_adapter.adapter import register as _register

__all__ = ["ServiceClientAdapter"]

_register()
