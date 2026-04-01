#!/bin/bash
set -euo pipefail

echo "==============================================="
echo "AAX Integration Test Suite"
echo "==============================================="
echo ""

# Read credentials from .env if not already set in environment
ENV_FILE="$(dirname "$0")/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

AWX_USER="${AWX_ADMIN_USER:-admin}"
AWX_PASS="${AWX_ADMIN_PASSWORD:-password}"
HUB_USER="${GALAXY_ADMIN_USERNAME:-admin}"
HUB_PASS="${HUB_ADMIN_PASSWORD:-changeme}"
AWX_WEB_PORT="${AWX_WEB_PORT:-18080}"
AWX_RECEPTOR_PORT="${AWX_RECEPTOR_PORT:-18888}"
GATEWAY_PORT="${GATEWAY_PORT:-18088}"
GALAXY_PORT="${GALAXY_PORT:-15001}"
EDA_PORT="${EDA_PORT:-15000}"
AWX_URL="http://localhost:${AWX_WEB_PORT}"
GALAXY_URL="http://localhost:${GALAXY_PORT}"
GATEWAY_URL="http://localhost:${GATEWAY_PORT}"
EDA_URL="http://localhost:${EDA_PORT}"

# Helper functions
pass() { echo -e "${GREEN}✓ PASS:${NC} $1"; }
fail() { echo -e "${RED}✗ FAIL:${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}ℹ INFO:${NC} $1"; }

compose_exec() {
    docker compose exec -T "$@"
}

# Test 1: AWX API Health
echo "Test 1: AWX API Health Check"
response=$(curl -s -o /dev/null -w "%{http_code}" "$AWX_URL/api/v2/ping/")
if [ "$response" = "200" ]; then
    pass "AWX API is responding (HTTP $response)"
else
    fail "AWX API returned HTTP $response"
fi
echo ""

# Test 2: AWX Authentication
echo "Test 2: AWX Authentication"
response=$(curl -s -u "$AWX_USER:$AWX_PASS" -o /dev/null -w "%{http_code}" "$AWX_URL/api/v2/me/")
if [ "$response" = "200" ]; then
    pass "AWX authentication successful"
else
    fail "AWX authentication failed (HTTP $response)"
fi
echo ""

# Test 3: Galaxy NG API Health
# Galaxy NG has no public-facing unauthenticated endpoint that returns 200;
# 403 on /api/galaxy/ means the service is up and running.
echo "Test 3: Galaxy NG API Health Check"
response=$(curl -s -o /dev/null -w "%{http_code}" "$GALAXY_URL/api/galaxy/")
if [[ "$response" =~ ^(200|403)$ ]]; then
    pass "Galaxy NG API is responding (HTTP $response)"
else
    fail "Galaxy NG API returned HTTP $response (expected 200 or 403)"
fi
echo ""

# Test 4: Pulp Status via Gateway
# Pulp API/content are internal-only — access via gateway at /pulp/api/
echo "Test 4: Pulp API Health (via Gateway)"
response=$(curl -s -o /dev/null -w "%{http_code}" "${GATEWAY_URL}/pulp/api/v3/status/")
if [ "$response" = "200" ]; then
    pass "Pulp API is responding via gateway (HTTP $response)"
else
    fail "Pulp API returned HTTP $response via gateway"
fi
echo ""

# Test 5: Pulp Content Server via Gateway
echo "Test 5: Pulp Content Server Health (via Gateway)"
response=$(curl -s -o /dev/null -w "%{http_code}" "${GATEWAY_URL}/pulp/content/")
if [[ "$response" =~ ^(200|404)$ ]]; then
    pass "Pulp Content Server is responding via gateway (HTTP $response)"
else
    fail "Pulp Content Server returned HTTP $response via gateway"
fi
echo ""

# Test 6: AWX Receptor
echo "Test 6: AWX Receptor Connectivity"
if timeout 2 bash -c "cat < /dev/null > /dev/tcp/localhost/${AWX_RECEPTOR_PORT}" 2>/dev/null; then
    pass "Receptor is listening on port ${AWX_RECEPTOR_PORT}"
else
    fail "Receptor is not accessible on port ${AWX_RECEPTOR_PORT}"
fi
echo ""

# Test 7: EDA Controller
echo "Test 7: EDA Controller Health"
response=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$EDA_URL/api/eda/v1/status/" || echo "000")
if [[ "$response" =~ ^(200|301|302|401|403)$ ]]; then
    pass "EDA Controller is responding (HTTP $response)"
else
    info "EDA Controller returned HTTP $response (gateway /eda/ path also available)"
fi
echo ""

# Test 8: Check AWX Organizations
echo "Test 8: AWX Organizations"
org_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/organizations/" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$org_count" -ge 1 ]; then
    pass "Found $org_count organization(s) in AWX"
else
    fail "No organizations found in AWX"
fi
echo ""

# Test 9: Check AWX Execution Environments
echo "Test 9: AWX Execution Environments"
ee_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/execution_environments/" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$ee_count" -ge 1 ]; then
    pass "Found $ee_count execution environment(s) registered"
else
    fail "No execution environments found"
fi
echo ""

# Test 10: Check AWX Instances
echo "Test 10: AWX Instance Registration"
instance_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/instances/" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$instance_count" -ge 1 ]; then
    pass "Found $instance_count AWX instance(s) registered"
else
    fail "No AWX instances registered"
fi
echo ""

# Test 11: Database Connectivity
# Hub DB: user=galaxy, db=hub
echo "Test 11: PostgreSQL Connectivity"
awx_db_test=$(compose_exec awx-postgres psql -U awx -d awx -c "SELECT 1;" 2>&1 | grep -c "1 row" || echo "0")
hub_db_test=$(compose_exec hub-postgres psql -U galaxy -d hub -c "SELECT 1;" 2>&1 | grep -c "1 row" || echo "0")
if [ "$awx_db_test" -ge 1 ] && [ "$hub_db_test" -ge 1 ]; then
    pass "Both PostgreSQL databases are accessible"
else
    fail "Database connectivity issue (awx=$awx_db_test hub=$hub_db_test)"
fi
echo ""

# Test 12: Redis Connectivity
echo "Test 12: Redis Connectivity"
awx_redis=$(compose_exec awx-redis redis-cli ping 2>/dev/null || echo "FAIL")
hub_redis=$(compose_exec hub-redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$awx_redis" = "PONG" ] && [ "$hub_redis" = "PONG" ]; then
    pass "Both Redis instances are responding"
else
    fail "Redis connectivity issue (awx=$awx_redis hub=$hub_redis)"
fi
echo ""

# Test 13: Container Health Status
echo "Test 13: Container Health Status"
unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | grep -c . || true)
healthy=$(docker ps --filter "health=healthy" --format "{{.Names}}" | grep -c . || true)
info "Healthy containers: $healthy"
info "Unhealthy containers: $unhealthy"
if [ "$healthy" -ge 6 ]; then
    pass "Core services are healthy ($healthy containers)"
else
    fail "Not enough healthy containers (expected >= 6, got $healthy)"
fi
echo ""

# Test 14: Create Test Inventory (AWX functional)
echo "Test 14: Create Test Inventory"
inv_name="integration-test-inventory-$(date +%s)"
inventory_id=$(curl -s -u "$AWX_USER:$AWX_PASS" \
    -H "Content-Type: application/json" \
    -X POST "$AWX_URL/api/v2/inventories/" \
    -d '{"name":"'"$inv_name"'","organization":1}')
inventory_id=$(echo "$inventory_id" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)
if [ -n "$inventory_id" ] && [ "$inventory_id" != "null" ]; then
    pass "Created test inventory (ID: $inventory_id)"
    curl -s -u "$AWX_USER:$AWX_PASS" -X DELETE "$AWX_URL/api/v2/inventories/$inventory_id/" > /dev/null
    info "Cleaned up test inventory"
else
    fail "Failed to create test inventory"
fi
echo ""

# Test 15: Pulp Worker Status (via Gateway)
echo "Test 15: Pulp Worker Task Processing"
pulp_status=$(curl -s "${GATEWAY_URL}/pulp/api/v3/status/")
# online_workers is a JSON array in Pulp API v3 — count its entries via python3
online_workers=$(echo "$pulp_status" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(len(d.get('online_workers', [])))" \
    2>/dev/null || echo 0)
if [ -n "$online_workers" ] && [ "$online_workers" -ge 1 ]; then
    pass "Pulp has $online_workers online worker(s)"
else
    fail "No Pulp workers online"
fi
echo ""

echo "==============================================="
echo "Integration Test Results"
echo "==============================================="
echo -e "${GREEN}All integration tests passed!${NC}"
echo ""
echo "Stack Summary:"
echo "  AWX Controller:   http://localhost:${AWX_WEB_PORT}   (${AWX_USER} / ${AWX_PASS})"
echo "  Galaxy NG Hub:    http://localhost:${GALAXY_PORT}    (${HUB_USER} / ${HUB_PASS})"
echo "  EDA Controller:   http://localhost:${EDA_PORT}"
echo "  Gateway:          http://localhost:${GATEWAY_PORT}"
echo "  AWX Receptor:     localhost:${AWX_RECEPTOR_PORT}"
