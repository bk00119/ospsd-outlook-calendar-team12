"""OpenTelemetry tracing + metrics + structured logging for the Outlook service."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import structlog
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

if TYPE_CHECKING:
    from fastapi import FastAPI

_SERVICE_NAME = "outlook-client-service"
_METRIC_EXPORT_INTERVAL_MS = 15_000


def _build_resource() -> Resource:
    """Return the resource that tags every span and metric."""
    return Resource.create(
        {
            "service.name": _SERVICE_NAME,
            "service.version": os.getenv("APP_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("APP_ENV", "dev"),
        },
    )


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


def _build_tracer_provider(resource: Resource) -> TracerProvider:
    """Build a tracer provider configured for OTLP or console fallback."""
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    exporter = (
        OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        if endpoint
        else ConsoleSpanExporter()
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


def _build_meter_provider(resource: Resource) -> MeterProvider:
    """Build a meter provider configured for OTLP or console fallback."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    exporter = (
        OTLPMetricExporter(endpoint=f"{endpoint.rstrip('/')}/v1/metrics")
        if endpoint
        else ConsoleMetricExporter()
    )
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=_METRIC_EXPORT_INTERVAL_MS,
    )
    return MeterProvider(resource=resource, metric_readers=[reader])


def configure_telemetry(app: FastAPI) -> None:
    """Configure tracing, metrics, and structured logging; instrument the app."""
    _configure_structlog()

    resource = _build_resource()
    tracer_provider = _build_tracer_provider(resource)
    meter_provider = _build_meter_provider(resource)

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )
    RequestsInstrumentor().instrument(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )

    structlog.get_logger(_SERVICE_NAME).info(
        "telemetry_configured",
        otlp_endpoint_set=bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")),
    )


_meter = metrics.get_meter(_SERVICE_NAME)
slack_messages_processed = _meter.create_counter(
    "slack_messages_processed",
    description="Slack messages processed by the poller, labeled by outcome.",
)
