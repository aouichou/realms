# Mistral Realms — Observability

Full observability stack: OpenTelemetry distributed traces → Jaeger, 40+ Prometheus metrics with 15 alert rules → Grafana dashboards, and structured logging with request-scoped correlation IDs.

---

## Stack

| Component | Image | Port | Purpose |
|-----------|-------|------|---------|
| **Jaeger** | `jaegertracing/all-in-one:1.53` | 16686 (UI), 4317 (OTLP gRPC), 4318 (OTLP HTTP) | Distributed trace storage and visualization |
| **Prometheus** | `prom/prometheus:v2.48.1` | 9090 | Metrics collection and alerting |
| **Grafana** | `grafana/grafana:10.2.3` | 3001 | Dashboards and visualization |

All three are included in both production (`docker-compose.yml`) and development (`docker-compose.dev.yml`) stacks.

---

## Accessing the UIs

```
Jaeger:     http://localhost:16686
Prometheus: http://localhost:9090
Grafana:    http://localhost:3001  (default: admin/admin)
```

---

## What's Instrumented

### Distributed Tracing (OpenTelemetry → Jaeger)

Tracing is configured in `backend/app/observability/tracing.py`. The OTLP gRPC exporter sends spans to Jaeger at `jaeger:4317`.

#### Auto-Instrumented (via OpenTelemetry instrumentors)

| Library | What's Traced |
|---------|--------------|
| **FastAPI** | Every HTTP request becomes a span with method, path, status code, duration |
| **HTTPX** | All outbound HTTP calls — this captures **every Mistral API call** since the Mistral SDK uses httpx internally |
| **Redis** | All Redis operations (SET, GET, LPUSH, etc.) with key names |
| **SQLAlchemy** | All database queries with SQL statement, parameters, duration |

#### Custom Spans

| Decorator/Function | Usage |
|-------------------|-------|
| `@trace_async("span_name")` | Wraps any async function with a span. Records function arguments and captures exceptions. Used across services. |
| `trace_llm_call(model, tokens...)` | Creates `llm.mistral.chat` spans with LLM-specific attributes |

#### LLM-Specific Span Attributes

Every AI provider call creates a span with:
- `llm.vendor` — provider name (e.g., "mistral", "qwen", "groq")
- `llm.model` — model identifier (e.g., "mistral-small-latest")
- `llm.prompt_tokens` — input token count
- `llm.completion_tokens` — output token count
- `llm.total_tokens` — combined token count

### What a DM Narration Trace Looks Like

A single player action (`POST /api/v1/conversations/action`) generates a distributed trace spanning:

```
[FastAPI] POST /api/v1/conversations/action (parent)
├── [SQLAlchemy] SELECT character WHERE id = ?
├── [SQLAlchemy] SELECT game_session WHERE id = ?
├── [SQLAlchemy] SELECT companions WHERE character_id = ?
├── [Redis] GET session:{id}:state
├── [Redis] LRANGE session:{id}:messages
│
├── [Custom] embed_text (Mistral API - mistral-embed)
│   └── [HTTPX] POST https://api.mistral.ai/v1/embeddings
│
├── [SQLAlchemy] SELECT adventure_memories ORDER BY embedding <=> ?
│
├── [Custom] dm_engine.narrate
│   ├── [Custom] build_messages
│   ├── [Custom] call_dm_with_tools
│   │   ├── [HTTPX] POST https://api.mistral.ai/v1/chat/completions  ← tool call iteration 1
│   │   │   └── [Custom] llm.mistral.chat {model, tokens}
│   │   ├── [Custom] tool_executor.execute_tool (get_creature_stats)
│   │   │   └── [SQLAlchemy] SELECT creature WHERE name LIKE ?
│   │   ├── [HTTPX] POST https://api.mistral.ai/v1/chat/completions  ← tool call iteration 2
│   │   │   └── [Custom] llm.mistral.chat {model, tokens}
│   │   ├── [Custom] tool_executor.execute_tool (request_player_roll)
│   │   └── [HTTPX] POST https://api.mistral.ai/v1/chat/completions  ← final narration
│   │       └── [Custom] llm.mistral.chat {model, tokens}
│   └── [Custom] dm_supervisor.validate
│
├── [Custom] scene_detection
│   └── [Custom] image_service.generate (if scene change detected)
│       └── [HTTPX] POST https://api.mistral.ai/v1/agents/...
│
├── [SQLAlchemy] INSERT conversation_message
├── [Redis] RPUSH session:{id}:messages
├── [Custom] embed_text (for memory storage)
│   └── [HTTPX] POST https://api.mistral.ai/v1/embeddings
└── [SQLAlchemy] INSERT adventure_memory
```

This trace lets you see:
- Total request latency vs LLM API latency (usually 1-3s of the total is LLM)
- How many tool-calling iterations occurred
- Which tools were called and their DB query times
- Token counts per LLM call
- Whether scene detection triggered image generation
- Memory embedding and storage duration

### Uninstrumented Services

The following services lack custom tracing (they still get auto-instrumented HTTP/DB/Redis spans, but no service-level spans):
- CompanionService
- EffectsService
- ContentLinker
- ToolExecutor (individual tool executions)

---

## Prometheus Metrics

Metrics are collected by `MetricsCollector` in `backend/app/observability/metrics.py` (394 lines) and exposed at `GET /metrics`.

### Metric Inventory (40+ metrics)

#### HTTP
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request duration (8 buckets: .005–10s) |

#### LLM / AI
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `llm_requests_total` | Counter | model, status | Total LLM API calls |
| `llm_tokens_used` | Counter | model, type (prompt/completion/total) | Token consumption |
| `llm_request_duration_seconds` | Histogram | model | LLM call duration (6 buckets up to 30s) |

#### Database
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `db_query_duration_seconds` | Histogram | operation | Query duration |
| `db_connections_active` | Gauge | — | Active DB connections |

#### Redis
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `redis_operations_total` | Counter | operation | Total Redis operations |
| `redis_cache_hits` | Counter | — | Cache hit count |
| `redis_cache_misses` | Counter | — | Cache miss count |

#### Rate Limiting
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rate_limit_exceeded_total` | Counter | endpoint | Rate limit violations |
| `rate_limit_blocks_total` | Counter | — | DDoS auto-blocks triggered |

#### Auth
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `auth_attempts_total` | Counter | result (success/failure) | Login attempts |

#### Sessions
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `active_sessions` | Gauge | — | Currently active sessions |
| `active_conversations` | Gauge | — | Active conversation count |

#### Companions
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `companion_responses_total` | Counter | companion_type | Companion AI responses |
| `companion_response_duration_seconds` | Histogram | — | Companion response time |
| `active_companions` | Gauge | — | Active companion count |
| `companion_loyalty_changes` | Counter | direction | Loyalty increases/decreases |

#### Spells & Effects
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `spell_casts_total` | Counter | school, level | Spells cast |
| `active_effects` | Gauge | — | Active spell effects |
| `effect_applications_total` | Counter | effect_type | Effects applied |
| `effect_duration_ticks` | Counter | — | Effect duration ticks processed |

#### Content Enrichment
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `content_enrichments_total` | Counter | content_type | Content enrichment operations |
| `entity_links_created` | Counter | — | Entity cross-references created |
| `enrichment_cache_performance` | Counter | result (hit/miss) | Enrichment cache performance |

#### DM Tools
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `dm_tool_calls_total` | Counter | tool_name | Tool calls by name |
| `dm_tool_duration_seconds` | Histogram | tool_name | Tool execution duration |

#### Image Generation
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `image_generations_total` | Counter | status | Image generation attempts |
| `image_generation_duration_seconds` | Histogram | — | Generation duration |
| `image_cache_size_bytes` | Gauge | — | Image cache size |

---

## Alert Rules

15 alert rules defined in `observability/prometheus/alerts.yml` across 6 groups:

### Critical Alerts
| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighHTTPErrorRate` | >5% 5xx responses over 5 min | critical |
| `HighHTTPLatency` | P95 latency >2s over 5 min | warning |
| `LLMServiceHighErrorRate` | >10% LLM failures over 5 min | critical |
| `SlowDatabaseQueries` | P95 query time >1s over 5 min | warning |

### Companion System
| Alert | Condition | Severity |
|-------|-----------|----------|
| `CompanionResponseSlow` | P95 >5s over 5 min | warning |
| `CompanionHighErrorRate` | >10% failures over 5 min | warning |

### Spell & Effects
| Alert | Condition | Severity |
|-------|-----------|----------|
| `SpellEffectProcessingSlow` | Processing time threshold exceeded | warning |
| `SpellCastHighErrorRate` | >15% failures over 5 min | warning |

### Content System
| Alert | Condition | Severity |
|-------|-----------|----------|
| `ContentEnrichmentSlow` | <0.1 operations/s | warning |
| `ContentCacheLowHitRate` | <50% cache hits | warning |

### DM Tools
| Alert | Condition | Severity |
|-------|-----------|----------|
| `DMToolExecutionSlow` | P95 >2s over 5 min | warning |
| `DMToolHighErrorRate` | >10% failures over 5 min | warning |

### Image Generation
| Alert | Condition | Severity |
|-------|-----------|----------|
| `ImageGenerationSlow` | P95 >30s over 5 min | warning |
| `ImageGenerationHighErrorRate` | >20% failures over 5 min | warning |

### Infrastructure
| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighDatabaseConnections` | >80 active connections | warning |
| `LargeImageCacheSize` | >10GB cache | warning |
| `HighRateLimitViolations` | >10/s rate limit hits | warning |

---

## Structured Logging

Configured in `backend/app/observability/logger.py`.

### Format
```
2026-02-28 14:30:15,123 level=INFO logger=dm_engine module=dm_engine func=narrate line=342 request_id=abc-123 user_id=42 session_id=sess-456 | Starting narration for character Thorin
```

### Context Variables (ContextVars)
Request-scoped variables automatically propagated through async call chains:
- `request_id` — UUID generated per request (also sent as `X-Request-ID` response header)
- `user_id` — extracted from JWT authentication
- `session_id` — game session identifier
- `character_id` — active character

Set/cleared by `LogContext` context manager in the observability middleware.

### Usage
```python
from app.observability.logger import get_logger
logger = get_logger(__name__)
logger.info("Starting narration", extra={"character_name": "Thorin"})
```

---

## Grafana Setup

### Datasources (auto-provisioned)
- **Prometheus** (`http://prometheus:9090`) — default datasource
- **Jaeger** (`http://jaeger:16686`) — with `tracesToLogs` correlation on `request_id`, `user_id`, `character_id`

### Dashboard
Auto-provisioned from `observability/grafana/dashboards/mistral-realms-overview.json`.

---

## Prometheus Configuration

`observability/prometheus/prometheus.yml` scrapes:
- `backend:8000/metrics` (10s interval)
- `localhost:9090` (Prometheus self-monitoring)
- Optional exporters (not deployed): `node-exporter:9100`, `postgres-exporter:9187`, `redis-exporter:9121`

---

## Validation Script

`scripts/test-observability.sh` validates the full stack:

```bash
./scripts/test-observability.sh
```

Checks:
1. Prometheus health + targets up + alert rules loaded
2. Grafana health + datasources configured
3. Jaeger health
4. Backend `/metrics` endpoint responding
5. Backend `/health` endpoint responding

---

## Directory Structure

```
observability/
├── prometheus/
│   ├── prometheus.yml          # Scrape configuration
│   └── alerts.yml              # 15 alert rules in 6 groups
├── grafana/
│   ├── datasources/
│   │   └── datasources.yml    # Prometheus + Jaeger auto-provisioning
│   └── dashboards/
│       ├── dashboards.yml     # Dashboard provisioning config
│       └── mistral-realms-overview.json  # Main dashboard

backend/app/observability/
├── __init__.py
├── tracing.py                 # OpenTelemetry setup, @trace_async, trace_llm_call
├── metrics.py                 # MetricsCollector with 40+ Prometheus metrics
└── logger.py                  # StructuredFormatter, ContextVars, LogContext
```
