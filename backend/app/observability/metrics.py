"""
Prometheus metrics for monitoring
Provides counters, histograms, and gauges for key metrics
"""

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


class MetricsCollector:
    """Helper class for collecting metrics"""

    def __init__(self):
        self.registry = registry

    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

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

    def record_db_query(self, operation: str, duration: float):
        """Record database query metrics"""
        db_query_duration_seconds.labels(operation=operation).observe(duration)

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

    def record_rate_limit_violation(self, client_type: str, blocked: bool = False):
        """Record rate limiting metrics"""
        rate_limit_exceeded_total.labels(client_type=client_type).inc()
        if blocked:
            rate_limit_blocks_total.inc()

    def record_auth_attempt(self, success: bool):
        """Record authentication attempt"""
        status = "success" if success else "failure"
        auth_attempts_total.labels(status=status).inc()

    def record_dm_narration(self, duration: float, has_roll: bool, language: str):
        """Record DM narration metrics"""
        # Record duration (already tracked by LLM metrics, but specific to narration)
        # Record if narration included dice rolls
        if has_roll:
            http_requests_total.labels(
                method="dm_narration", endpoint="/narrate", status_code="200"
            ).inc()

    def set_active_connections(self, count: int):
        """Set active database connections gauge"""
        db_connections_active.set(count)

    def set_active_sessions(self, count: int):
        """Set active sessions gauge"""
        active_sessions.set(count)

    def set_active_conversations(self, count: int):
        """Set active conversations gauge"""
        active_conversations.set(count)

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics in text format"""
        return generate_latest(self.registry)


# Global metrics instance
metrics = MetricsCollector()
