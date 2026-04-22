"""OpenTelemetry tracing + structured logging setup for the Outlook service."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

if TYPE_CHECKING:
    from fastapi import FastAPI

_SERVICE_NAME = "outlook-client-service"


def _configure_structlog() -> None:
    """Configure structlog to emit JSON lines suitable for log aggregators."""
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _build_tracer_provider() -> TracerProvider:
    """Build a tracer provider configured for OTLP (Grafana Cloud) or console fallback."""
    resource = Resource.create(
        {
            "service.name": _SERVICE_NAME,
            "service.version": os.getenv("APP_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("APP_ENV", "dev"),
        },
    )
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")),
        )
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    return provider


def configure_telemetry(app: FastAPI) -> None:
    """Configure structured logging + OTel tracing and instrument the given app."""
    _configure_structlog()

    provider = _build_tracer_provider()
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()

    structlog.get_logger(_SERVICE_NAME).info(
        "telemetry_configured",
        otlp_endpoint_set=bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")),
    )
