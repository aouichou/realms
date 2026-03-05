"""
Prometheus metrics for monitoring
Provides counters, histograms, and gauges for key metrics.

Dual-write support: records to both prometheus_client (for /metrics scraping)
and OpenTelemetry (for OTLP push to Grafana Cloud) when configured.
"""

from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

# Create a custom registry to avoid conflicts
registry = CollectorRegistry()

# HTTP Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry,
)

# LLM metrics
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "status"],
    registry=registry,
)

llm_tokens_used = Counter(
    "llm_tokens_used",
    "Total tokens used in LLM calls",
    ["model", "type"],  # type: prompt, completion, total
    registry=registry,
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=registry,
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],  # SELECT, INSERT, UPDATE, DELETE
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=registry,
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=registry,
)

# Redis metrics
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],  # operation: get, set, delete
    registry=registry,
)

redis_cache_hits = Counter(
    "redis_cache_hits",
    "Total Redis cache hits",
    registry=registry,
)

redis_cache_misses = Counter(
    "redis_cache_misses",
    "Total Redis cache misses",
    registry=registry,
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors by type",
    ["error_type", "endpoint"],
    registry=registry,
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["client_type"],  # ip, user
    registry=registry,
)

rate_limit_blocks_total = Counter(
    "rate_limit_blocks_total",
    "Total rate limit blocks (DDoS protection)",
    registry=registry,
)

# Authentication metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["status"],  # success, failure
    registry=registry,
)

# User session metrics
active_sessions = Gauge(
    "active_sessions",
    "Number of active user sessions",
    registry=registry,
)

active_conversations = Gauge(
    "active_conversations",
    "Number of active AI conversations",
    registry=registry,
)

# Companion metrics
companion_responses_total = Counter(
    "companion_responses_total",
    "Total companion AI responses generated",
    ["companion_name", "status"],
    registry=registry,
)

companion_response_duration_seconds = Histogram(
    "companion_response_duration_seconds",
    "Companion AI response generation time",
    ["companion_name"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0),
    registry=registry,
)

active_companions = Gauge(
    "active_companions",
    "Number of currently active companions",
    registry=registry,
)

companion_loyalty_changes = Counter(
    "companion_loyalty_changes",
    "Total companion loyalty changes",
    ["direction"],  # increase, decrease
    registry=registry,
)

# Spell effect metrics
spell_casts_total = Counter(
    "spell_casts_total",
    "Total spells cast",
    ["spell_name", "level", "success"],
    registry=registry,
)

active_effects_gauge = Gauge(
    "active_effects",
    "Number of currently active spell effects",
    ["effect_type"],
    registry=registry,
)

effect_applications_total = Counter(
    "effect_applications_total",
    "Total spell effects applied",
    ["effect_name", "result"],  # success, failure, resisted
    registry=registry,
)

effect_duration_ticks = Histogram(
    "effect_duration_ticks",
    "How long effects last (in ticks/rounds)",
    ["effect_name"],
    buckets=(1, 3, 5, 10, 20, 60),
    registry=registry,
)

# Content enrichment metrics
content_enrichments_total = Counter(
    "content_enrichments_total",
    "Total content enrichment operations",
    ["entity_type"],  # spell, item, creature, location
    registry=registry,
)

entity_links_created = Counter(
    "entity_links_created",
    "Total entity links created",
    ["entity_type"],
    registry=registry,
)

enrichment_cache_performance = Counter(
    "enrichment_cache_performance",
    "Content enrichment cache hits/misses",
    ["result"],  # hit, miss
    registry=registry,
)

# Character creation metrics
character_creations_total = Counter(
    "character_creations_total",
    "Total characters created",
    ["character_class", "race"],
    registry=registry,
)

# DM tool metrics
dm_tool_calls_total = Counter(
    "dm_tool_calls_total",
    "Total DM tool executions",
    ["tool_name", "status"],
    registry=registry,
)

dm_tool_duration_seconds = Histogram(
    "dm_tool_duration_seconds",
    "DM tool execution time",
    ["tool_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0),
    registry=registry,
)

# Image generation metrics
image_generations_total = Counter(
    "image_generations_total",
    "Total image generations requested",
    ["status", "source"],  # status: success/failure/cached, source: mistral/cache
    registry=registry,
)

image_generation_duration_seconds = Histogram(
    "image_generation_duration_seconds",
    "Image generation time",
    buckets=(1.0, 5.0, 10.0, 20.0, 30.0, 60.0),
    registry=registry,
)

image_cache_size_bytes = Gauge(
    "image_cache_size_bytes",
    "Total size of image cache",
    registry=registry,
)


class MetricsCollector:
    """Helper class for collecting metrics.

    Records to prometheus_client for /metrics scraping and optionally
    to OpenTelemetry for OTLP push to Grafana Cloud.
    """

    def __init__(self):
        self.registry = registry
        # OTel instruments (initialized lazily via init_otel_instruments)
        self._otel_enabled = False
        self._otel = {}

    def init_otel_instruments(self):
        """Initialize OpenTelemetry metric instruments for dual-write."""
        from app.observability.tracing import get_meter

        meter = get_meter("mistral-realms")

        self._otel = {
            "http_requests": meter.create_counter(
                "http.requests", description="Total HTTP requests", unit="1"
            ),
            "http_duration": meter.create_histogram(
                "http.request.duration", description="HTTP request duration", unit="s"
            ),
            "llm_requests": meter.create_counter(
                "llm.requests", description="Total LLM API requests", unit="1"
            ),
            "llm_tokens": meter.create_counter(
                "llm.tokens.used", description="Total tokens used", unit="1"
            ),
            "llm_duration": meter.create_histogram(
                "llm.request.duration", description="LLM request duration", unit="s"
            ),
            "db_duration": meter.create_histogram(
                "db.query.duration", description="Database query duration", unit="s"
            ),
            "errors": meter.create_counter("errors", description="Total errors by type", unit="1"),
            "rate_limit_exceeded": meter.create_counter(
                "rate_limit.exceeded", description="Rate limit violations", unit="1"
            ),
            "auth_attempts": meter.create_counter(
                "auth.attempts", description="Authentication attempts", unit="1"
            ),
            "image_generations": meter.create_counter(
                "image.generations", description="Image generations", unit="1"
            ),
            "image_gen_duration": meter.create_histogram(
                "image.generation.duration", description="Image generation time", unit="s"
            ),
            "active_sessions": meter.create_up_down_counter(
                "sessions.active", description="Active user sessions", unit="1"
            ),
            "character_creations": meter.create_counter(
                "character.creations", description="Characters created", unit="1"
            ),
        }
        self._otel_enabled = True

    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        if self._otel_enabled:
            attrs = {"http.method": method, "http.route": endpoint, "http.status_code": status}
            self._otel["http_requests"].add(1, attrs)
            self._otel["http_duration"].record(duration, attrs)

    def record_llm_request(
        self,
        model: str,
        status: str,
        duration: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        """Record LLM request metrics"""
        llm_requests_total.labels(model=model, status=status).inc()
        llm_request_duration_seconds.labels(model=model).observe(duration)
        llm_tokens_used.labels(model=model, type="prompt").inc(prompt_tokens)
        llm_tokens_used.labels(model=model, type="completion").inc(completion_tokens)
        llm_tokens_used.labels(model=model, type="total").inc(prompt_tokens + completion_tokens)
        if self._otel_enabled:
            attrs = {"llm.model": model, "llm.status": status}
            self._otel["llm_requests"].add(1, attrs)
            self._otel["llm_duration"].record(duration, attrs)
            self._otel["llm_tokens"].add(prompt_tokens, {**attrs, "token.type": "prompt"})
            self._otel["llm_tokens"].add(completion_tokens, {**attrs, "token.type": "completion"})

    def record_db_query(self, operation: str, duration: float):
        """Record database query metrics"""
        db_query_duration_seconds.labels(operation=operation).observe(duration)
        if self._otel_enabled:
            self._otel["db_duration"].record(duration, {"db.operation": operation})

    def record_redis_operation(
        self, operation: str, status: str, is_cache: bool = False, hit: bool = False
    ):
        """Record Redis operation metrics"""
        redis_operations_total.labels(operation=operation, status=status).inc()
        if is_cache:
            if hit:
                redis_cache_hits.inc()
            else:
                redis_cache_misses.inc()

    def record_error(self, error_type: str, endpoint: str):
        """Record error metrics"""
        errors_total.labels(error_type=error_type, endpoint=endpoint).inc()
        if self._otel_enabled:
            self._otel["errors"].add(1, {"error.type": error_type, "http.route": endpoint})

    def record_rate_limit_violation(self, client_type: str, blocked: bool = False):
        """Record rate limiting metrics"""
        rate_limit_exceeded_total.labels(client_type=client_type).inc()
        if blocked:
            rate_limit_blocks_total.inc()
        if self._otel_enabled:
            self._otel["rate_limit_exceeded"].add(
                1, {"client.type": client_type, "blocked": str(blocked)}
            )

    def record_auth_attempt(self, success: bool):
        """Record authentication attempt"""
        status = "success" if success else "failure"
        auth_attempts_total.labels(status=status).inc()
        if self._otel_enabled:
            self._otel["auth_attempts"].add(1, {"auth.status": status})

    def record_dm_narration(self, duration: float, has_roll: bool, language: str):
        """Record DM narration metrics"""
        # Record duration (already tracked by LLM metrics, but specific to narration)
        # Record if narration included dice rolls
        if has_roll:
            http_requests_total.labels(
                method="dm_narration", endpoint="/narrate", status="200"
            ).inc()

    def record_character_creation(self, character_class: str, race: str):
        """Record character creation event"""
        character_creations_total.labels(character_class=character_class, race=race).inc()
        if self._otel_enabled:
            self._otel["character_creations"].add(
                1, {"character.class": character_class, "character.race": race}
            )

    def set_active_connections(self, count: int):
        """Set active database connections gauge"""
        db_connections_active.set(count)

    def set_active_sessions(self, count: int):
        """Set active sessions gauge"""
        active_sessions.set(count)

    def set_active_conversations(self, count: int):
        """Set active conversations gauge"""
        active_conversations.set(count)

    def record_companion_response(self, companion_name: str, status: str, duration: float):
        """Record companion AI response metrics"""
        companion_responses_total.labels(companion_name=companion_name, status=status).inc()
        companion_response_duration_seconds.labels(companion_name=companion_name).observe(duration)

    def record_companion_loyalty_change(self, direction: str):
        """Record companion loyalty change"""
        companion_loyalty_changes.labels(direction=direction).inc()

    def set_active_companions(self, count: int):
        """Set active companions gauge"""
        active_companions.set(count)

    def record_spell_cast(self, spell_name: str, level: int, success: bool):
        """Record spell cast"""
        status = "success" if success else "failure"
        spell_casts_total.labels(spell_name=spell_name, level=str(level), success=status).inc()

    def set_active_effects(self, effect_type: str, count: int):
        """Set active effects gauge for specific type"""
        active_effects_gauge.labels(effect_type=effect_type).set(count)

    def record_effect_application(self, effect_name: str, result: str):
        """Record effect application"""
        effect_applications_total.labels(effect_name=effect_name, result=result).inc()

    def record_effect_duration(self, effect_name: str, ticks: int):
        """Record effect duration in ticks"""
        effect_duration_ticks.labels(effect_name=effect_name).observe(ticks)

    def record_content_enrichment(self, entity_type: str):
        """Record content enrichment operation"""
        content_enrichments_total.labels(entity_type=entity_type).inc()

    def record_entity_link(self, entity_type: str):
        """Record entity link creation"""
        entity_links_created.labels(entity_type=entity_type).inc()

    def record_enrichment_cache(self, hit: bool):
        """Record enrichment cache performance"""
        result = "hit" if hit else "miss"
        enrichment_cache_performance.labels(result=result).inc()

    def record_dm_tool_execution(self, tool_name: str, status: str, duration: float):
        """Record DM tool execution"""
        dm_tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        dm_tool_duration_seconds.labels(tool_name=tool_name).observe(duration)

    def record_image_generation(self, status: str, source: str, duration: Optional[float] = None):
        """Record image generation"""
        image_generations_total.labels(status=status, source=source).inc()
        if duration is not None:
            image_generation_duration_seconds.observe(duration)
        if self._otel_enabled:
            attrs = {"image.status": status, "image.source": source}
            self._otel["image_generations"].add(1, attrs)
            if duration is not None:
                self._otel["image_gen_duration"].record(duration, attrs)

    def set_image_cache_size(self, size_bytes: int):
        """Set image cache size gauge"""
        image_cache_size_bytes.set(size_bytes)

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics in text format"""
        return generate_latest(self.registry)


# Global metrics instance
metrics = MetricsCollector()
