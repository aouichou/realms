"""
OpenTelemetry distributed tracing
Provides tracing for FastAPI, SQLAlchemy, and custom operations.

Supports two backends:
- Local Jaeger (gRPC, insecure) for development
- Grafana Cloud (OTLP/HTTP with basic-auth) for production
"""

import base64
import functools
import logging
from typing import Any, Callable, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHTTPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer: Optional[trace.Tracer] = None


def _build_grafana_auth_header(instance_id: str, api_key: str) -> str:
    """Build base64-encoded Basic auth header for Grafana Cloud OTLP."""
    credentials = f"{instance_id}:{api_key}"
    return base64.b64encode(credentials.encode()).decode()


def init_tracing(
    service_name: str = "mistral-realms-backend",
    otlp_endpoint: str = "http://jaeger:4317",
    enabled: bool = True,
    grafana_otlp_endpoint: str = "",
    grafana_instance_id: str = "",
    grafana_api_key: str = "",
) -> None:
    """
    Initialize OpenTelemetry tracing.

    When Grafana Cloud credentials are provided, exports via OTLP/HTTP
    with basic-auth to Grafana Cloud. Otherwise falls back to local
    Jaeger via gRPC.

    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP gRPC endpoint for local Jaeger
        enabled: Whether tracing is enabled
        grafana_otlp_endpoint: Grafana Cloud OTLP gateway URL
        grafana_instance_id: Grafana Cloud instance ID (numeric)
        grafana_api_key: Grafana Cloud API key
    """
    global _tracer

    if not enabled:
        return

    # Create resource with service name
    resource = Resource(attributes={SERVICE_NAME: service_name})

    # Set up tracer provider
    provider = TracerProvider(resource=resource)

    # Choose exporter: Grafana Cloud (OTLP/HTTP) or local Jaeger (gRPC)
    if grafana_otlp_endpoint and grafana_instance_id and grafana_api_key:
        auth_b64 = _build_grafana_auth_header(grafana_instance_id, grafana_api_key)
        otlp_exporter = OTLPHTTPSpanExporter(
            endpoint=f"{grafana_otlp_endpoint.rstrip('/')}/v1/traces",
            headers={"Authorization": f"Basic {auth_b64}"},
        )
        logger.info("Tracing exporter: Grafana Cloud OTLP/HTTP → %s", grafana_otlp_endpoint)
    else:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        logger.info("Tracing exporter: local Jaeger gRPC → %s", otlp_endpoint)

    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Get tracer
    _tracer = trace.get_tracer(__name__)


def instrument_app(app) -> None:
    """
    Instrument FastAPI application with auto-instrumentation

    Args:
        app: FastAPI application instance
    """
    # FastAPI auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)

    # HTTPX client instrumentation (for Mistral API calls)
    HTTPXClientInstrumentor().instrument()

    # Redis instrumentation
    RedisInstrumentor().instrument()


def instrument_sqlalchemy(engine) -> None:
    """
    Instrument SQLAlchemy engine for query tracing

    Args:
        engine: SQLAlchemy engine instance
    """
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


def trace_async(span_name: Optional[str] = None):
    """
    Decorator for tracing async functions

    Args:
        span_name: Optional custom span name (defaults to function name)

    Usage:
        @trace_async("create_character")
        async def create_character(data: dict):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add function arguments as attributes
                if args:
                    span.set_attribute("args.count", len(args))
                if kwargs:
                    for key, value in kwargs.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"arg.{key}", value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


class trace_llm_call:  # noqa: N801
    """
    Context manager for tracing LLM API calls.

    Creates an OpenTelemetry span with LLM-specific attributes (model, vendor,
    token usage, duration, status). Token counts can be set after the call
    completes via set_usage().

    Usage:
        with TraceLLMCall("mistral-small-latest", vendor="mistral") as span_ctx:
            response = await mistral_client.chat(...)
            span_ctx.set_usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
    """

    def __init__(
        self,
        model: str,
        vendor: str = "mistral",
        operation: str = "chat",
    ):
        self.model = model
        self.vendor = vendor
        self.operation = operation
        self._span: Optional[Any] = None

    def set_usage(
        self,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ):
        """Set token usage attributes on the span after the LLM call completes."""
        if self._span is None:
            return
        if prompt_tokens is not None:
            self._span.set_attribute("llm.prompt_tokens", prompt_tokens)
        if completion_tokens is not None:
            self._span.set_attribute("llm.completion_tokens", completion_tokens)
        if total_tokens is not None:
            self._span.set_attribute("llm.total_tokens", total_tokens)

    def __enter__(self):
        tracer = get_tracer()
        self._span = tracer.start_span(f"llm.{self.vendor}.{self.operation}")
        self._span.set_attribute("llm.vendor", self.vendor)
        self._span.set_attribute("llm.model", self.model)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._span is None:
            return False
        if exc_type is not None:
            self._span.set_attribute("llm.status", "error")
            self._span.set_attribute("error.type", exc_type.__name__)
            self._span.set_attribute("error.message", str(exc_val))
            self._span.record_exception(exc_val)
        else:
            self._span.set_attribute("llm.status", "success")
        self._span.end()
        return False
