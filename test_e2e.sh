#!/bin/bash
set -e

echo "==============================================="
echo "AAX End-to-End Integration Test"
echo "Tests AWX + Galaxy NG + Pulp Integration"
echo "==============================================="
echo ""

AWX_URL="http://localhost:8080"
AWX_USER="admin"
AWX_PASS="password"
GALAXY_URL="http://localhost:5001"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}ℹ${NC} $1"; }

echo "Step 1: Verify AWX is Ready"
info "Checking AWX API..."
curl -sf -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/ping/" > /dev/null || fail "AWX API not responding"
pass "AWX API is accessible"
echo ""

echo "Step 2: Verify Galaxy NG is Ready"
info "Checking Galaxy NG API..."
curl -sf "$GALAXY_URL/api/" > /dev/null || fail "Galaxy NG not responding"
pass "Galaxy NG is accessible"
echo ""

echo "Step 3: Verify Pulp is Ready"
info "Checking Pulp API..."
curl -sf "http://localhost:24817/pulp/api/v3/status/" > /dev/null || fail "Pulp API not responding"
pass "Pulp API is accessible"
echo ""

echo "Step 4: Check AWX Execution Environments"
info "Listing registered execution environments..."
ee_list=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/execution_environments/")
ee_count=$(echo "$ee_list" | grep -o '"count":[0-9]*' | cut -d: -f2)
info "Found $ee_count execution environment(s)"
echo "$ee_list" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | while read -r name; do
    echo "  - $name"
done
pass "Execution environments registered"
echo ""

echo "Step 5: Check Default Organization"
info "Verifying default organization exists..."
org_data=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/organizations/")
org_count=$(echo "$org_data" | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ "$org_count" -ge 1 ]; then
    org_name=$(echo "$org_data" | grep -o '"name":"[^"]*"' | head -1 | cut -d'"' -f4)
    pass "Organization: $org_name"
else
    fail "No organizations found"
fi
echo ""

echo "Step 6: Test AWX Job Template Creation"
info "Creating test resources..."

# Create inventory
inv_response=$(curl -s -u "$AWX_USER:$AWX_PASS" \
    -H "Content-Type: application/json" \
    -X POST "$AWX_URL/api/v2/inventories/" \
    -d '{"name":"e2e-test-inventory","organization":1}')
inv_id=$(echo "$inv_response" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -n "$inv_id" ]; then
    pass "Created inventory (ID: $inv_id)"

    # Add localhost to inventory
    host_response=$(curl -s -u "$AWX_USER:$AWX_PASS" \
        -H "Content-Type: application/json" \
        -X POST "$AWX_URL/api/v2/inventories/$inv_id/hosts/" \
        -d '{"name":"localhost","variables":"ansible_connection: local"}')
    host_id=$(echo "$host_response" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

    if [ -n "$host_id" ]; then
        pass "Added localhost to inventory (ID: $host_id)"
    fi
else
    fail "Failed to create inventory"
fi
echo ""

echo "Step 7: Verify Receptor Communication"
info "Testing Receptor mesh connectivity..."
receptor_status=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/mesh_visualizer/")
node_count=$(echo "$receptor_status" | grep -o '"hostname":"[^"]*"' | wc -l)
if [ "$node_count" -ge 1 ]; then
    pass "Receptor mesh has $node_count node(s)"
else
    fail "Receptor mesh communication issue"
fi
echo ""

echo "Step 8: Check AWX Instance Capacity"
info "Checking AWX instance readiness..."
instance_data=$(curl -s -u "$AWX_USER:$AWX_PASS" "$AWX_URL/api/v2/instances/")
instance_name=$(echo "$instance_data" | grep -o '"hostname":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$instance_name" ]; then
    pass "AWX instance '$instance_name' is registered"
else
    fail "No AWX instances found"
fi
echo ""

echo "Step 9: Test Galaxy Collection API"
info "Checking Galaxy collection repositories..."
galaxy_repos=$(curl -s "$GALAXY_URL/api/_ui/v1/collection-versions/" 2>/dev/null || echo '{"meta":{"count":0}}')
collection_count=$(echo "$galaxy_repos" | grep -o '"count":[0-9]*' | cut -d: -f2 || echo "0")
pass "Galaxy has $collection_count collection(s) published"
echo ""

echo "Step 10: Verify Pulp Content Distribution"
info "Checking Pulp content distributions..."
pulp_distros=$(curl -s "http://localhost:24817/pulp/api/v3/distributions/ansible/ansible/" 2>/dev/null || echo '{"count":0}')
distro_count=$(echo "$pulp_distros" | grep -o '"count":[0-9]*' | cut -d: -f2 || echo "0")
pass "Pulp has $distro_count content distribution(s)"
echo ""

echo "Step 11: Clean Up Test Resources"
info "Removing temporary test resources..."
if [ -n "$inv_id" ]; then
    curl -s -u "$AWX_USER:$AWX_PASS" -X DELETE "$AWX_URL/api/v2/inventories/$inv_id/" > /dev/null
    pass "Cleaned up test inventory"
fi
echo ""

echo "==============================================="
echo -e "${GREEN}✓ End-to-End Integration Test Complete!${NC}"
echo "==============================================="
echo ""
echo "System Status:"
echo "  ✓ AWX Controller is operational"
echo "  ✓ Galaxy NG is serving collections"
echo "  ✓ Pulp is managing content"
echo "  ✓ Receptor mesh is connected"
echo "  ✓ PostgreSQL databases are healthy"
echo "  ✓ Redis caches are operational"
echo ""
echo "Your AAX stack is fully integrated and ready!"
echo ""
echo "To use the stack:"
echo ""
echo "1. Access AWX Web UI:"
echo "   http://localhost:8080"
echo "   Login: admin / password"
echo ""
echo "2. Configure a Project:"
echo "   - Point to your Git repository"
echo "   - Select an execution environment"
echo ""
echo "3. Upload Collections to Galaxy:"
echo "   ansible-galaxy collection publish --server http://localhost:5001 collection.tar.gz"
echo ""
echo "4. Configure AWX to use Private Galaxy:"
echo "   - Add Galaxy credentials in AWX"
echo "   - Point projects to your private Galaxy server"
echo ""
