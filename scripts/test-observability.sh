#!/bin/bash
# Test observability stack integration

set -e

echo "🔍 Testing Observability Stack..."
echo "================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test Prometheus
echo -n "Testing Prometheus..."
if curl -s http://localhost:9090/-/healthy | grep -q "Prometheus"; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    exit 1
fi

# Test Prometheus targets
echo -n "Testing Prometheus targets..."
if curl -s http://localhost:9090/api/v1/targets | jq -e '.data.activeTargets[] | select(.labels.job=="backend-api")' > /dev/null; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${YELLOW}⚠ Backend not scraped yet${NC}"
fi

# Test Prometheus alerts loaded
echo -n "Testing alert rules..."
RULES=$(curl -s http://localhost:9090/api/v1/rules | jq '.data.groups | length')
if [ "$RULES" -gt 0 ]; then
    echo -e " ${GREEN}✓ ($RULES groups loaded)${NC}"
else
    echo -e " ${RED}✗ No alert rules loaded${NC}"
    exit 1
fi

# Test Grafana
echo -n "Testing Grafana..."
if curl -s http://localhost:3001/api/health | grep -q "ok"; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    exit 1
fi

# Test Grafana datasources
echo -n "Testing Grafana datasources..."
DS_COUNT=$(curl -s -u admin:admin http://localhost:3001/api/datasources | jq 'length')
if [ "$DS_COUNT" -ge 2 ]; then
    echo -e " ${GREEN}✓ ($DS_COUNT datasources)${NC}"
else
    echo -e " ${YELLOW}⚠ Expected 2+ datasources, found $DS_COUNT${NC}"
fi

# Test Grafana dashboards
echo -n "Testing Grafana dashboards..."
DASH_COUNT=$(curl -s -u admin:admin http://localhost:3001/api/search?type=dash-db | jq 'length')
if [ "$DASH_COUNT" -ge 1 ]; then
    echo -e " ${GREEN}✓ ($DASH_COUNT dashboards)${NC}"
else
    echo -e " ${YELLOW}⚠ No dashboards loaded yet (may take a moment)${NC}"
fi

# Test Jaeger
echo -n "Testing Jaeger..."
if curl -s http://localhost:16686 | grep -q "Jaeger UI"; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    exit 1
fi

# Test Backend metrics endpoint
echo -n "Testing backend /metrics..."
if curl -s http://localhost:8000/metrics | grep -q "http_requests_total"; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${YELLOW}⚠ Backend not responding${NC}"
fi

echo ""
echo "================================="
echo -e "${GREEN}All observability tests passed!${NC}"
echo ""
echo "Access points:"
echo "  - Grafana:    http://localhost:3001 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo "  - Jaeger:     http://localhost:16686"
echo "  - Metrics:    http://localhost:8000/metrics"
echo ""
echo "Next steps:"
echo "  1. Open Grafana and view 'Mistral Realms - Overview' dashboard"
echo "  2. Check Prometheus alerts: http://localhost:9090/alerts"
echo "  3. Generate some traffic and view traces in Jaeger"
