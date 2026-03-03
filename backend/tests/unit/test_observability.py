"""Tests for app.observability.metrics and app.observability.tracing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# MetricsCollector
# ============================================================================


class TestMetricsCollector:
    def _make_collector(self):
        from app.observability.metrics import MetricsCollector

        return MetricsCollector()

    def test_record_http_request(self):
        mc = self._make_collector()
        mc.record_http_request("GET", "/api/test", 200, 0.05)
        # No exception = success

    def test_record_llm_request(self):
        mc = self._make_collector()
        mc.record_llm_request(
            "mistral-small", "success", 1.5, prompt_tokens=100, completion_tokens=50
        )

    def test_record_db_query(self):
        mc = self._make_collector()
        mc.record_db_query("SELECT", 0.01)

    def test_record_redis_operation(self):
        mc = self._make_collector()
        mc.record_redis_operation("get", "success", is_cache=True, hit=True)
        mc.record_redis_operation("set", "success", is_cache=True, hit=False)
        mc.record_redis_operation("delete", "success")

    def test_record_error(self):
        mc = self._make_collector()
        mc.record_error("ValueError", "/api/chars")

    def test_record_rate_limit_violation(self):
        mc = self._make_collector()
        mc.record_rate_limit_violation("ip")
        mc.record_rate_limit_violation("user", blocked=True)

    def test_record_auth_attempt(self):
        mc = self._make_collector()
        mc.record_auth_attempt(success=True)
        mc.record_auth_attempt(success=False)

    def test_set_active_connections(self):
        mc = self._make_collector()
        mc.set_active_connections(10)

    def test_set_active_sessions(self):
        mc = self._make_collector()
        mc.set_active_sessions(5)

    def test_set_active_conversations(self):
        mc = self._make_collector()
        mc.set_active_conversations(3)

    def test_record_companion_response(self):
        mc = self._make_collector()
        mc.record_companion_response("Thalia", "success", 2.0)

    def test_record_companion_loyalty_change(self):
        mc = self._make_collector()
        mc.record_companion_loyalty_change("increase")

    def test_set_active_companions(self):
        mc = self._make_collector()
        mc.set_active_companions(2)

    def test_record_spell_cast(self):
        mc = self._make_collector()
        mc.record_spell_cast("Fireball", 3, True)

    def test_set_active_effects(self):
        mc = self._make_collector()
        mc.set_active_effects("buff", 5)

    def test_record_effect_application(self):
        mc = self._make_collector()
        mc.record_effect_application("Shield", "success")

    def test_record_effect_duration(self):
        mc = self._make_collector()
        mc.record_effect_duration("Shield", 10)

    def test_record_content_enrichment(self):
        mc = self._make_collector()
        mc.record_content_enrichment("spell")

    def test_record_entity_link(self):
        mc = self._make_collector()
        mc.record_entity_link("item")

    def test_record_enrichment_cache(self):
        mc = self._make_collector()
        mc.record_enrichment_cache(hit=True)
        mc.record_enrichment_cache(hit=False)

    def test_record_dm_tool_execution(self):
        mc = self._make_collector()
        mc.record_dm_tool_execution("request_player_roll", "success", 0.5)

    def test_record_image_generation(self):
        mc = self._make_collector()
        mc.record_image_generation("success", "mistral", duration=5.0)
        mc.record_image_generation("failure", "cache")

    def test_set_image_cache_size(self):
        mc = self._make_collector()
        mc.set_image_cache_size(1024)

    def test_generate_metrics(self):
        mc = self._make_collector()
        output = mc.generate_metrics()
        assert isinstance(output, bytes)
        assert len(output) > 0

    def test_record_dm_narration(self):
        mc = self._make_collector()
        mc.record_dm_narration(1.5, has_roll=True, language="en")
        mc.record_dm_narration(0.8, has_roll=False, language="fr")

    @patch("app.observability.metrics.MetricsCollector.init_otel_instruments")
    def test_otel_dual_write(self, mock_init):
        mc = self._make_collector()
        # Simulate OTel instruments initialised
        mc._otel_enabled = True
        mc._otel = {
            "http_requests": MagicMock(),
            "http_duration": MagicMock(),
            "llm_requests": MagicMock(),
            "llm_tokens": MagicMock(),
            "llm_duration": MagicMock(),
            "db_duration": MagicMock(),
            "errors": MagicMock(),
            "rate_limit_exceeded": MagicMock(),
            "auth_attempts": MagicMock(),
            "image_generations": MagicMock(),
            "image_gen_duration": MagicMock(),
        }
        mc.record_http_request("POST", "/api/x", 201, 0.1)
        mc._otel["http_requests"].add.assert_called_once()
        mc._otel["http_duration"].record.assert_called_once()

        mc.record_llm_request("model", "success", 1.0, 10, 20)
        mc._otel["llm_requests"].add.assert_called_once()

        mc.record_db_query("INSERT", 0.02)
        mc._otel["db_duration"].record.assert_called_once()

        mc.record_error("TypeError", "/test")
        mc._otel["errors"].add.assert_called_once()

        mc.record_rate_limit_violation("ip")
        mc._otel["rate_limit_exceeded"].add.assert_called_once()

        mc.record_auth_attempt(True)
        mc._otel["auth_attempts"].add.assert_called_once()

        mc.record_image_generation("success", "mistral", 2.0)
        mc._otel["image_generations"].add.assert_called_once()
        mc._otel["image_gen_duration"].record.assert_called_once()


# ============================================================================
# Tracing utilities
# ============================================================================


class TestBuildGrafanaAuthHeader:
    def test_encodes_correctly(self):
        from app.observability.tracing import _build_grafana_auth_header

        result = _build_grafana_auth_header("12345", "my-api-key")
        import base64

        decoded = base64.b64decode(result).decode()
        assert decoded == "12345:my-api-key"


class TestGetTracer:
    def test_returns_tracer(self):
        from app.observability.tracing import get_tracer

        tracer = get_tracer()
        assert tracer is not None


class TestGetMeter:
    def test_returns_meter(self):
        from app.observability.tracing import get_meter

        meter = get_meter("test")
        assert meter is not None


class TestTraceAsync:
    async def test_decorator_calls_function(self):
        from app.observability.tracing import trace_async

        @trace_async("test_span")
        async def my_func(x):
            return x * 2

        result = await my_func(5)
        assert result == 10

    async def test_decorator_propagates_exception(self):
        from app.observability.tracing import trace_async

        @trace_async()
        async def failing_func():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await failing_func()

    async def test_decorator_default_span_name(self):
        from app.observability.tracing import trace_async

        @trace_async()
        async def my_named_func():
            return 42

        result = await my_named_func()
        assert result == 42


class TestTraceLLMCall:
    def test_context_manager_success(self):
        from app.observability.tracing import trace_llm_call

        with trace_llm_call("mistral-small", vendor="mistral") as ctx:
            ctx.set_usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        # No exception

    def test_context_manager_error(self):
        from app.observability.tracing import trace_llm_call

        with pytest.raises(ValueError):
            with trace_llm_call("mistral-small") as ctx:
                raise ValueError("api error")

    def test_set_usage_no_span(self):
        from app.observability.tracing import trace_llm_call

        ctx = trace_llm_call("model")
        # Before __enter__, _span is None
        ctx.set_usage(10, 20, 30)  # should not raise


class TestInitTracing:
    @patch("app.observability.tracing.trace")
    @patch("app.observability.tracing.TracerProvider")
    @patch("app.observability.tracing.BatchSpanProcessor")
    @patch("app.observability.tracing.OTLPSpanExporter")
    def test_init_local_jaeger(self, mock_exporter, mock_processor, mock_provider, mock_trace):
        from app.observability.tracing import init_tracing

        init_tracing(enabled=True, otlp_endpoint="http://localhost:4317")
        mock_exporter.assert_called_once()
        mock_provider.assert_called_once()

    def test_init_disabled(self):
        from app.observability.tracing import init_tracing

        # Should return without doing anything
        init_tracing(enabled=False)

    @patch("app.observability.tracing.trace")
    @patch("app.observability.tracing.TracerProvider")
    @patch("app.observability.tracing.BatchSpanProcessor")
    @patch("app.observability.tracing.OTLPHTTPSpanExporter")
    def test_init_grafana_cloud(
        self, mock_http_exporter, mock_processor, mock_provider, mock_trace
    ):
        from app.observability.tracing import init_tracing

        init_tracing(
            enabled=True,
            grafana_otlp_endpoint="https://otlp.grafana.net",
            grafana_instance_id="12345",
            grafana_api_key="secret",
        )
        mock_http_exporter.assert_called_once()


class TestInitMetricsExport:
    def test_no_credentials_skips(self):
        from app.observability.tracing import init_metrics_export

        # Should not raise
        init_metrics_export()

    @patch("app.observability.tracing.otel_metrics")
    @patch("app.observability.tracing.MeterProvider")
    @patch("app.observability.tracing.PeriodicExportingMetricReader")
    @patch("app.observability.tracing.OTLPMetricExporter")
    def test_with_credentials(self, mock_exporter, mock_reader, mock_provider, mock_otel):
        from app.observability.tracing import init_metrics_export

        init_metrics_export(
            grafana_otlp_endpoint="https://otlp.grafana.net",
            grafana_instance_id="12345",
            grafana_api_key="secret",
            export_interval_ms=30000,
        )
        mock_exporter.assert_called_once()
        mock_provider.assert_called_once()
