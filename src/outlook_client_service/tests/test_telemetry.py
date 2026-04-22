"""Unit tests for telemetry configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from outlook_client_service.telemetry import configure_telemetry


def test_configure_telemetry_installs_tracer_provider_without_otlp_endpoint() -> None:
    """Fall back to console exporter when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""
    app = FastAPI()

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)
        configure_telemetry(app)

    assert isinstance(trace.get_tracer_provider(), TracerProvider)


def test_configure_telemetry_uses_otlp_endpoint_when_set() -> None:
    """Use the OTLP HTTP exporter when an endpoint is configured."""
    app = FastAPI()

    with patch.dict(
        os.environ,
        {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp.example.com"},
    ):
        configure_telemetry(app)

    assert isinstance(trace.get_tracer_provider(), TracerProvider)
