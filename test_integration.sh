#!/bin/bash
set -e

echo "==============================================="
echo "AAX Integration Test Suite"
echo "==============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

AWX_URL="http://localhost:8080"
AWX_USER="admin"
AWX_PASS="password"
GALAXY_URL="http://localhost:5001"
PULP_API_URL="http://localhost:24817"

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
}

fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    exit 1
}

info() {
    echo -e "${YELLOW}ℹ INFO:${NC} $1"
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

# Test 3: Pulp API Health
echo "Test 3: Pulp API Health Check"
response=$(curl -s -o /dev/null -w "%{http_code}" "$PULP_API_URL/pulp/api/v3/status/")
if [ "$response" = "200" ]; then
    pass "Pulp API is responding (HTTP $response)"
else
    fail "Pulp API returned HTTP $response"
fi
echo ""

# Test 4: Pulp Content Server
echo "Test 4: Pulp Content Server Health"
response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:24816/pulp/content/")
if [ "$response" = "200" ] || [ "$response" = "404" ]; then
    pass "Pulp Content Server is responding (HTTP $response)"
else
    fail "Pulp Content Server returned HTTP $response"
fi
echo ""

# Test 5: Galaxy NG API
echo "Test 5: Galaxy NG API Health"
response=$(curl -s -o /dev/null -w "%{http_code}" "$GALAXY_URL/api/")
if [ "$response" = "200" ]; then
    pass "Galaxy NG API is responding (HTTP $response)"
else
    fail "Galaxy NG API returned HTTP $response"
fi
echo ""

# Test 6: AWX Receptor
echo "Test 6: AWX Receptor Connectivity"
if timeout 2 bash -c "cat < /dev/null > /dev/tcp/localhost/8888" 2>/dev/null; then
    pass "Receptor is listening on port 8888"
else
    fail "Receptor is not accessible on port 8888"
fi
echo ""

# Test 7: Check AWX Organizations
echo "Test 7: AWX Organizations"
org_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/organizations/" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$org_count" -ge 1 ]; then
    pass "Found $org_count organization(s) in AWX"
else
    fail "No organizations found in AWX"
fi
echo ""

# Test 8: Check AWX Execution Environments
echo "Test 8: AWX Execution Environments"
ee_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/execution_environments/" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$ee_count" -ge 1 ]; then
    pass "Found $ee_count execution environment(s) registered"
else
    fail "No execution environments found"
fi
echo ""

# Test 9: Check AWX Instances
echo "Test 9: AWX Instance Registration"
instance_count=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/instances/" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$instance_count" -ge 1 ]; then
    pass "Found $instance_count AWX instance(s) registered"
else
    fail "No AWX instances registered"
fi
echo ""

# Test 10: Database Connectivity
echo "Test 10: PostgreSQL Connectivity"
awx_db_test=$(docker exec awx-postgres psql -U awx -d awx -c "SELECT 1;" 2>&1 | grep -c "1 row")
hub_db_test=$(docker exec hub-postgres psql -U pulp -d pulp -c "SELECT 1;" 2>&1 | grep -c "1 row")
if [ "$awx_db_test" -ge 1 ] && [ "$hub_db_test" -ge 1 ]; then
    pass "Both PostgreSQL databases are accessible"
else
    fail "Database connectivity issue detected"
fi
echo ""

# Test 11: Redis Connectivity
echo "Test 11: Redis Connectivity"
awx_redis=$(docker exec awx-redis redis-cli ping 2>/dev/null || echo "FAIL")
hub_redis=$(docker exec hub-redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$awx_redis" = "PONG" ] && [ "$hub_redis" = "PONG" ]; then
    pass "Both Redis instances are responding"
else
    fail "Redis connectivity issue detected"
fi
echo ""

# Test 12: Container Health Status
echo "Test 12: Container Health Status"
unhealthy=$(docker ps --filter "health=unhealthy" --format "{{.Names}}" | wc -l)
healthy=$(docker ps --filter "health=healthy" --format "{{.Names}}" | wc -l)
info "Healthy containers: $healthy"
info "Unhealthy containers: $unhealthy"
if [ "$healthy" -ge 6 ]; then
    pass "Core services are healthy"
else
    fail "Not enough healthy containers (expected >= 6, got $healthy)"
fi
echo ""

# Test 13: Create Test Inventory
echo "Test 13: Create Test Inventory"
inventory_id=$(curl -s -u "$AWX_USER:$AWX_PASS" \
    -H "Content-Type: application/json" \
    -X POST "$AWX_URL/api/v2/inventories/" \
    -d '{"name":"integration-test-inventory","organization":1}' \
    | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
if [ -n "$inventory_id" ] && [ "$inventory_id" != "null" ]; then
    pass "Created test inventory (ID: $inventory_id)"

    # Clean up
    curl -s -u "$AWX_USER:$AWX_PASS" -X DELETE "$AWX_URL/api/v2/inventories/$inventory_id/" > /dev/null
    info "Cleaned up test inventory"
else
    fail "Failed to create test inventory"
fi
echo ""

# Test 14: Pulp Worker Status
echo "Test 14: Pulp Worker Task Processing"
pulp_status=$(curl -s "$PULP_API_URL/pulp/api/v3/status/" | grep -o '"online_workers":[0-9]*' | cut -d: -f2)
if [ -n "$pulp_status" ] && [ "$pulp_status" -ge 1 ]; then
    pass "Pulp has $pulp_status online worker(s)"
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
echo "  - AWX Controller: http://localhost:8080 (admin/password)"
echo "  - Galaxy NG: http://localhost:5001"
echo "  - Pulp API: http://localhost:24817"
echo "  - Pulp Content: http://localhost:24816"
echo "  - Receptor: localhost:8888"
echo ""
echo "Next Steps:"
echo "  1. Log into AWX UI at http://localhost:8080"
echo "  2. Create a project pointing to a Git repository"
echo "  3. Create credentials for your infrastructure"
echo "  4. Build custom execution environments"
echo "  5. Upload collections to your private Galaxy"
echo ""
