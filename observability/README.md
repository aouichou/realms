# Observability Stack Setup

Complete observability infrastructure for Mistral Realms with Prometheus, Grafana, and Jaeger.

## Architecture

```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│   FastAPI   │────▶│  Prometheus   │────▶│   Grafana    │
│   Backend   │     │  (Metrics)    │     │ (Dashboards) │
└─────────────┘     └───────────────┘     └──────────────┘
       │                                          │
       │            ┌───────────────┐            │
       └───────────▶│    Jaeger     │────────────┘
                    │   (Traces)    │
                    └───────────────┘
```

## Quick Start

### 1. Start the Observability Stack

```bash
# From project root
docker-compose up -d prometheus grafana jaeger

# Verify services are running
docker-compose ps
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3001
  - Username: `admin`
  - Password: `admin` (change on first login)
  - Pre-loaded dashboard: "Mistral Realms - Overview"

- **Prometheus**: http://localhost:9090
  - Metrics explorer
  - Alert rules status

- **Jaeger**: http://localhost:16686
  - Distributed tracing
  - Service dependency graph

### 3. View Metrics

```bash
# Check backend metrics endpoint
curl http://localhost:8000/metrics

# View specific metrics
curl http://localhost:8000/metrics | grep companion_responses_total
curl http://localhost:8000/metrics | grep spell_casts_total
```

## Files Structure

```
observability/
├── prometheus/
│   ├── prometheus.yml          # Prometheus configuration
│   └── alerts.yml              # Alerting rules
├── grafana/
│   ├── datasources/
│   │   └── datasources.yml     # Prometheus & Jaeger datasources
│   ├── provisioning/
│   │   └── dashboards.yml      # Dashboard provisioning
│   └── dashboards/
│       └── mistral-realms-overview.json  # Main dashboard
└── README.md                   # This file
```

## Dashboard Features

The **Mistral Realms - Overview** dashboard includes:

### HTTP Metrics
- Request rate per second
- P95 latency gauge with thresholds
- Error rate by endpoint

### LLM & AI Metrics
- Token usage rate (Mistral + Gemini)
- P95 LLM response latency
- Model comparison

### Companion System (RL-131)
- Companion response rate by status
- P95 response time with SLA thresholds (5s warning)
- Active companions gauge
- Loyalty change tracking

### Spell Effects (RL-106)
- Spell cast rate by level
- Active effects by type (pie chart)
- Effect application success/failure
- Effect duration tracking

### Content System (RL-145)
- Content enrichment rate by entity type
- Entity link creation rate
- Cache hit/miss ratio

### DM Tools
- Tool execution rate
- Tool-specific latency
- Error rates per tool

### Database & Redis
- Query P95 latency
- Active connections
- Cache performance

### Infrastructure
- Database connections gauge
- Redis operation stats
- Rate limiting violations

## Alert Rules

### Critical Alerts
- **HighHTTPErrorRate**: >5% error rate for 5min
- **LLMServiceHighErrorRate**: >10% LLM errors for 2min
- **CompanionHighErrorRate**: >10% companion errors for 5min

### Warning Alerts
- **HighHTTPLatency**: P95 >2s for 5min
- **CompanionResponseSlow**: P95 >5s for 3min
- **SpellEffectProcessingSlow**: P95 >100ms for 5min
- **SlowDatabaseQueries**: P95 >1s for 5min
- **DMToolExecutionSlow**: P95 >2s for 5min

### Info Alerts
- **ImageGenerationSlow**: P95 >30s for 3min
- **ContentCacheLowHitRate**: <50% hit rate for 10min
- **LargeImageCacheSize**: >10GB for 10min

## Prometheus Configuration

### Scrape Targets

1. **backend-api** (10s interval)
   - Endpoint: `http://backend:8000/metrics`
   - All application metrics

2. **prometheus** (15s interval)
   - Self-monitoring

3. **node-exporter** (optional)
   - System metrics (CPU, memory, disk)

4. **postgres-exporter** (optional)
   - Database-specific metrics

5. **redis-exporter** (optional)
   - Redis-specific metrics

### Alert Evaluation

- Interval: 30s
- Alert file: `/etc/prometheus/alerts.yml`

## Grafana Configuration

### Pre-configured Datasources

1. **Prometheus** (default)
   - URL: `http://prometheus:9090`
   - Scrape interval: 15s

2. **Jaeger**
   - URL: `http://jaeger:16686`
   - Trace-to-logs integration

### Dashboard Auto-loading

Dashboards in `observability/grafana/dashboards/` are automatically loaded on startup.

### Customization

1. Edit dashboard in Grafana UI
2. Export JSON via "Share" → "Export"
3. Save to `observability/grafana/dashboards/`
4. Restart Grafana: `docker-compose restart grafana`

## Jaeger Tracing

### Service Name
- `mistral-realms-backend`

### Traced Operations
- All HTTP endpoints (auto-instrumented)
- LLM calls (Mistral + Gemini)
- Database queries (SQLAlchemy)
- Companion AI operations
- Spell effect processing
- DM tool executions
- Content enrichment

### Viewing Traces

1. Open Jaeger UI: http://localhost:16686
2. Select service: `mistral-realms-backend`
3. Search by:
   - Operation name (e.g., "POST /api/v1/conversations/:id/action")
   - Tags (e.g., `http.status_code=500`)
   - Duration (e.g., `>2s`)

### Correlation IDs

All traces include correlation IDs:
- `request_id`: Unique request identifier
- `user_id`: Authenticated user
- `character_id`: Active character
- `session_id`: Game session

Match these with structured logs for full debugging context.

## Alerting Setup (Optional)

### Alertmanager Integration

1. Add to `docker-compose.yml`:
```yaml
alertmanager:
  image: prom/alertmanager:v0.26.0
  ports:
    - "9093:9093"
  volumes:
    - ./observability/alertmanager.yml:/etc/alertmanager/alertmanager.yml
  command:
    - '--config.file=/etc/alertmanager/alertmanager.yml'
```

2. Uncomment alerting section in `prometheus.yml`

3. Create `alertmanager.yml`:
```yaml
route:
  receiver: 'slack'
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

## Debug Logging

Debug-level logs are now available for:

### ContentLinker (RL-145)
```python
logger.debug("Entity matches for {monster.name}", extra={
    "monster_id": ...,
    "cr": ...,
    "matched_items": [...],
    "item_categories": [...]
})
```

### EffectsService (RL-106)
```python
logger.debug("Processing effect tick: {effect.name}", extra={
    "effect_id": ...,
    "rounds_remaining": ...,
    "requires_concentration": ...
})
```

### CompanionService (RL-131)
```python
logger.debug("Loyalty calculation for {companion.name}", extra={
    "old_loyalty": ...,
    "loyalty_change": ...,
    "new_loyalty": ...,
    "was_clamped": ...
})
```

Enable debug logging:
```bash
# In docker-compose.yml or .env
LOG_LEVEL=DEBUG
```

## Performance Budgets

Monitored SLAs:
- ✅ HTTP requests: P95 <2s
- ✅ Companion responses: P95 <5s
- ✅ Spell effects: P95 <100ms
- ✅ Content enrichment: P95 <500ms
- ✅ Image generation: P95 <30s
- ✅ Database queries: P95 <1s

## Metrics Retention

### Prometheus
- Default: 15 days
- Modify in `docker-compose.yml`:
```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=30d'
```

### Jaeger
- Default: In-memory (ephemeral)
- For persistence, add Elasticsearch backend:
```yaml
jaeger:
  environment:
    - SPAN_STORAGE_TYPE=elasticsearch
    - ES_SERVER_URLS=http://elasticsearch:9200
```

## Troubleshooting

### Metrics Not Appearing

1. Check backend metrics endpoint:
```bash
curl http://localhost:8000/metrics
```

2. Check Prometheus targets:
- Visit http://localhost:9090/targets
- Ensure `backend:8000` is **UP**

3. Check Prometheus logs:
```bash
docker-compose logs prometheus
```

### Dashboard Not Loading

1. Verify datasource:
- Grafana → Configuration → Data Sources
- Test connection to Prometheus

2. Check dashboard file:
```bash
cat observability/grafana/dashboards/mistral-realms-overview.json | jq .
```

3. Reload provisioning:
```bash
docker-compose restart grafana
```

### Traces Not in Jaeger

1. Check tracing is enabled:
```bash
# In backend container
env | grep TRACING_ENABLED
```

2. Verify Jaeger connection:
```bash
curl http://localhost:16686/api/services
```

3. Check backend logs:
```bash
docker-compose logs backend | grep -i otlp
```

### Alerts Not Firing

1. Check alert rules:
- Visit http://localhost:9090/alerts
- Verify rules are loaded

2. Manually trigger alert:
```bash
# Force high error rate
for i in {1..100}; do curl http://localhost:8000/nonexistent; done
```

3. Check alert state:
```bash
# Should transition: Inactive → Pending → Firing
```

## Next Steps

1. **Create Custom Dashboards**
   - Copy `mistral-realms-overview.json`
   - Customize for specific use cases
   - Add to provisioning directory

2. **Set Up Alertmanager**
   - Configure Slack/PagerDuty integration
   - Define escalation policies
   - Test alert notifications

3. **Add Log Aggregation**
   - Deploy Loki for log aggregation
   - Link traces to logs in Grafana
   - Create log-based alerts

4. **Enable Advanced Features**
   - Query performance insights
   - User session analytics
   - Business metrics (quest completion rates)

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Tutorials](https://grafana.com/tutorials/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Best Practices](https://opentelemetry.io/docs/concepts/observability-primer/)
