#!/bin/bash
set -euo pipefail

echo "==============================================="
echo "AAX Stack Integration Test (Working Components)"
echo "==============================================="
echo ""

# Read credentials from .env if not already set in environment
if [ -f "$(dirname "$0")/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$(dirname "$0")/.env"
    set +a
fi

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

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}→${NC} $1"; }

wait_for_awx_api() {
    local attempts="${1:-60}"
    local delay_seconds="${2:-5}"
    local i

    for ((i=1; i<=attempts; i++)); do
        if curl -sf "$AWX_URL/api/v2/ping/" > /dev/null; then
            return 0
        fi
        info "AWX not ready yet (attempt ${i}/${attempts}), waiting ${delay_seconds}s..."
        sleep "$delay_seconds"
    done

    return 1
}

echo "=== Testing AWX Controller ==="
echo ""

info "1. Checking AWX API health..."
if ! docker ps --format '{{.Names}}' | grep -qx 'awx-web'; then
    fail "awx-web container is not running. Start stack with: docker compose up -d"
fi

wait_for_awx_api 60 5 || fail "AWX API not responding after 300s. Check logs with: docker compose logs awx-web awx-task"
pass "AWX API is operational"

info "2. Testing AWX authentication..."
curl -sf -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/me/" > /dev/null || fail "Authentication failed"
pass "AWX authentication successful"

info "3. Checking AWX organizations..."
org_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/organizations/" | grep -o '"count":[0-9]*' | cut -d: -f2)
pass "Found $org_count organization(s)"

info "4. Checking execution environments..."
ee_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/execution_environments/" | grep -o '"count":[0-9]*' | cut -d: -f2)
pass "Found $ee_count execution environment(s)"

info "5. Checking AWX instances..."
instance_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/instances/" | grep -o '"count":[0-9]*' | cut -d: -f2)
pass "Found $instance_count AWX instance(s) registered"

info "6. Testing Receptor mesh connectivity..."
mesh_data=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/mesh_visualizer/")
node_count=$(echo "$mesh_data" | grep -o '"hostname":"[^"]*"' | wc -l | tr -d ' ')
if [ "$node_count" -ge 1 ]; then
    pass "Receptor mesh has $node_count node(s)"
else
    fail "Receptor mesh communication issue"
fi

echo ""
echo "=== Testing Private Automation Hub ==="
echo ""

# Pulp API/content have no host ports — they're internal-only.
# Access via Gateway (port ${GATEWAY_PORT}) which proxies:
#   /pulp/api/      → pulp-api:24817
#   /pulp/content/  → pulp-content:24816
#   /api/galaxy/    → galaxy-ng:8000

info "7. Checking Galaxy NG API..."
# Galaxy NG returns 403 for unauthenticated — that still means the service is up
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$GALAXY_URL/api/galaxy/")
if [[ "$http_code" =~ ^(200|403)$ ]]; then
    pass "Galaxy NG API is operational (HTTP $http_code)"
else
    fail "Galaxy NG API returned unexpected HTTP $http_code (expected 200 or 403)"
fi

info "8. Checking Pulp workers (via gateway)..."
pulp_status=$(curl -s "${GATEWAY_URL}/pulp/api/v3/status/")
# online_workers is a JSON array in Pulp API v3 — count its entries via python3
worker_count=$(echo "$pulp_status" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(len(d.get('online_workers', [])))" \
    2>/dev/null || echo 0)
if [ -n "$worker_count" ] && [ "$worker_count" -ge 1 ]; then
    pass "Pulp has $worker_count online worker(s)"
else
    fail "No Pulp workers online"
fi

info "9. Checking Pulp content server (via gateway)..."
content_code=$(curl -s -o /dev/null -w "%{http_code}" "${GATEWAY_URL}/pulp/content/")
if [[ "$content_code" =~ ^(200|404)$ ]]; then
    pass "Pulp content server is operational (HTTP $content_code)"
else
    fail "Pulp content server returned unexpected HTTP $content_code"
fi

echo ""
echo "=== Testing Infrastructure ==="
echo ""

info "10. Checking PostgreSQL databases..."
awx_db=$(docker exec awx-postgres psql -U awx -d awx -c "SELECT count(*) FROM main_organization;" 2>&1 | grep -E "^\s+[0-9]+$" | tr -d ' ' || echo "0")
hub_db=$(docker exec aax-hub-postgres psql -U galaxy -d hub -c "SELECT 1;" 2>&1 | grep -c "1 row" || echo "0")
if [ "$awx_db" -ge 1 ] && [ "$hub_db" -ge 1 ]; then
    pass "PostgreSQL databases operational (AWX has $awx_db org(s))"
else
    fail "Database connectivity issue (awx_orgs=$awx_db hub_rows=$hub_db)"
fi

info "11. Checking Redis..."
awx_redis=$(docker exec awx-redis redis-cli ping 2>/dev/null || echo "FAIL")
hub_redis=$(docker exec aax-hub-redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$awx_redis" = "PONG" ] && [ "$hub_redis" = "PONG" ]; then
    pass "All Redis instances responding"
else
    fail "Redis connectivity issue (awx=$awx_redis hub=$hub_redis)"
fi

info "12. Checking container health..."
healthy=$(docker ps --filter "health=healthy" --format "{{.Names}}" | wc -l)
unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | tr '\n' ' ')
pass "$healthy containers report healthy status"
if [ -n "$unhealthy" ]; then
    echo -e "${YELLOW}  Warning: unhealthy containers: $unhealthy${NC}"
fi

echo ""
echo "=== Functional Tests ==="
echo ""

info "13. Creating test inventory..."
inv_name="integration-test-inventory-$(date +%s)"
inv_response=$(curl -s -u "$AWX_USER:$AWX_PASS" \
    -H "Content-Type: application/json" \
    -X POST "$AWX_URL/api/v2/inventories/" \
    -d '{"name":"'"$inv_name"'","organization":1}')
inv_id=$(echo "$inv_response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)

if [ -n "$inv_id" ] && [ "$inv_id" != "null" ]; then
    pass "Created test inventory (ID: $inv_id)"

    info "14. Adding host to inventory..."
    host_response=$(curl -s -u "$AWX_USER:$AWX_PASS" \
        -H "Content-Type: application/json" \
        -X POST "$AWX_URL/api/v2/inventories/$inv_id/hosts/" \
        -d '{"name":"test-host","variables":"ansible_connection: local"}')
    host_id=$(echo "$host_response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || true)

    if [ -n "$host_id" ]; then
        pass "Added test host (ID: $host_id)"
    else
        fail "Failed to add test host"
    fi

    info "15. Cleaning up test resources..."
    curl -s -u "$AWX_USER:$AWX_PASS" -X DELETE "$AWX_URL/api/v2/inventories/$inv_id/" > /dev/null
    pass "Test inventory removed"
else
    fail "Failed to create test inventory: $inv_response"
fi

echo ""
echo "==============================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "==============================================="
echo ""
echo "Working Services:"
echo "  AWX Controller  http://localhost:${AWX_WEB_PORT}  (${AWX_USER} / ${AWX_PASS})"
echo "  AWX Receptor    port ${AWX_RECEPTOR_PORT}"
echo "  Galaxy NG Hub   http://localhost:${GALAXY_PORT}   (${HUB_USER} / ${HUB_PASS})"
echo "  EDA Controller  http://localhost:${EDA_PORT}"
echo "  Gateway (all)   http://localhost:${GATEWAY_PORT}"
echo "    /api/galaxy/    -> Galaxy NG"
echo "    /pulp/api/      -> Pulp API"
echo "    /pulp/content/  -> Pulp content"
echo "    /eda/           -> EDA Controller"
echo "    /               -> AWX Web UI"
echo "  PostgreSQL      AWX & Hub/Pulp"
echo "  Redis           AWX & Hub"
echo ""
echo "Next Steps:"
echo "  1. Login to AWX:  http://localhost:${AWX_WEB_PORT}"
echo "  2. Login to Hub:  http://localhost:${GALAXY_PORT}"
echo "  3. Create a project, credentials, and job templates"
echo "  4. Run automation jobs"
echo ""
