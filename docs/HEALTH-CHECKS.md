# Health Check Endpoints

This document lists the health check endpoints and monitoring capabilities for all AAX services.

## Docker Health Checks

Each container includes a built-in health check that Docker Compose and Kubernetes use to determine service readiness.

### ee-base

**Health Check Command:**

```bash
python3 -c "import ansible; import ansible_runner"
```

**Status:**

- Returns `0` if Ansible modules can be imported
- Runs every 30 seconds
- Considered unhealthy after 3 consecutive failures

**Test manually:**

```bash
docker compose exec ee-base python3 -c "import ansible; import ansible_runner" && echo "HEALTHY" || echo "UNHEALTHY"
```

---

### ee-builder

**Health Check Command:**

```bash
ansible-builder --version
```

**Status:**

- Returns `0` if ansible-builder CLI is functional
- Runs every 30 seconds
- Considered unhealthy after 3 consecutive failures

**Test manually:**

```bash
docker compose exec ee-builder ansible-builder --version && echo "HEALTHY" || echo "UNHEALTHY"
```

---

### dev-tools

**Health Check Command:**

```bash
ansible-navigator --version
```

**Status:**

- Returns `0` if ansible-navigator is available
- Runs every 30 seconds
- Considered unhealthy after 3 consecutive failures

**Test manually:**

```bash
docker compose exec dev-tools ansible-navigator --version && echo "HEALTHY" || echo "UNHEALTHY"
```

---

## AWX API Health Endpoints

### Status/Ping Endpoint

**URL:**

``` text
GET /api/v2/ping/
```

**Response:**

```json
{
  "ha_enabled": false,
  "ha_mode": false,
  "install_uuid": "00000000-0000-0000-0000-000000000000",
  "instances": [],
  "license_info": {
    "license_type": "community"
  },
  "version": "24.6.1"
}
```

**Status Codes:**

- `200 OK` - Service is healthy
- `503 Service Unavailable` - Database connection failed

**Test:**

```bash
curl http://localhost:8080/api/v2/ping/
```

---

### System Health Endpoint

**URL:**

```text
GET /api/v2/system_jobs/
```

**Response includes:** Background job metrics, migration status

**Test:**

```bash
curl -u admin:password http://localhost:8080/api/v2/system_jobs/
```

---

## Galaxy NG Health Endpoints

### Status Endpoint

**URL:**

```text
GET /api/galaxy/v3/status/
```

**Response:**

```json
{
  "pulp_version": "3.28.43",
  "component_versions": {
    "galaxy_ng": "4.9.2"
  }
}
```

**Status Codes:**

- `200 OK` - Service is healthy
- `503 Service Unavailable` - Database or Pulp unavailable

**Test:**

```bash
curl http://localhost:8000/api/galaxy/v3/status/
```

---

### Kubernetes Status

**URL:**

```text
/-/ready/
```

**Response:** Text response

**Test:**

```bash
curl http://localhost:8000/-/ready/
```

---

## Pulp API Health Endpoints

### System Status Endpoint

**URL:**

```text
GET /pulp/api/v3/status/
```

**Response:**

```json
{
  "database_connection": {
    "connected": true
  },
  "redis_connection": {
    "connected": true
  },
  "pulp_version": "3.28.43",
  "components": {
    "pulp_ansible": "0.20.12"
  }
}
```

**Status Codes:**

- `200 OK` - All systems healthy
- `503 Service Unavailable` - Database or Redis unavailable

**Test:**

```bash
curl http://localhost:24816/pulp/api/v3/status/
```

---

## Event-Driven Ansible Health Endpoints

### Health Endpoint

**URL:**

```text
GET /health
```

**Response:**

```json
{
  "status": "running",
  "version": "1.1.3"
}
```

**Status Codes:**

- `200 OK` - Service is running
- `503 Service Unavailable` - Service is unhealthy

**Test:**

```bash
curl http://localhost:5000/health
```

---

## Kubernetes Pod Health Checks

### Check All Pod Status

```bash
kubectl get pods -n aax -o wide
```

### Check Specific Pod Details

```bash
kubectl describe pod -n aax <pod-name>
```

### View Health Check Results

```bash
kubectl get events -n aax --sort-by='.lastTimestamp'
```

---

## Monitoring Health Checks

### Docker Compose

**View health status:**

```bash
docker compose ps
```

**Example output:**

```text
NAME                  IMAGE                           STATUS
awx-web               aax/awx:latest                  Up (healthy)
ee-base               aax/ee-base:latest              Up (healthy)
ee-builder            aax/ee-builder:latest           Up (healthy)
dev-tools             aax/dev-tools:latest            Up (healthy)
galaxy-ng             aax/galaxy-ng:latest            Up (healthy)
pulp                  aax/pulp:latest                 Up (healthy)
eda                   aax/eda:latest                  Up (healthy)
```

**Check logs for health check failures:**

```bash
docker compose logs | grep -i "health\|check\|failed"
```

---

### Kubernetes

**View pod readiness:**

```bash
kubectl get pods -n aax -o custom-columns=NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status
```

**Watch pod status changes:**

```bash
kubectl get pods -n aax --watch
```

---

## Troubleshooting Unhealthy Services

### If a service is unhealthy

1. **Check service logs:**

   ```bash
   docker compose logs <service-name>
   # or
   kubectl logs -n aax deployment/<service-name>
   ```

2. **Test health endpoint directly:**

   ```bash
   # AWX
   curl -v http://localhost:8080/api/v2/ping/

   # Galaxy
   curl -v http://localhost:8000/api/galaxy/v3/status/

   # Pulp
   curl -v http://localhost:24816/pulp/api/v3/status/

   # EDA
   curl -v http://localhost:5000/health
   ```

3. **Check database connectivity:**

   ```bash
   docker compose exec <service-name> psql -h postgres -U awx -d awx -c "SELECT 1;"
   ```

4. **Check Redis connectivity:**

   ```bash
   docker compose exec <service-name> redis-cli -h redis ping
   ```

5. **Restart service:**

   ```bash
   docker compose restart <service-name>
   # or
   kubectl rollout restart -n aax deployment/<service-name>
   ```

---

## Automated Health Monitoring

### Docker Compose Health Check Script

```bash
#!/bin/bash
# Check all services and report status

echo "=== AAX Health Check ==="
services=(awx-web ee-base ee-builder dev-tools galaxy-ng pulp eda)

for service in "${services[@]}"; do
    status=$(docker compose ps | grep "$service" | awk '{print $5}')
    echo "$service: $status"
done
```

### Kubernetes Health Check Script

```bash
#!/bin/bash
# Check Kubernetes pod readiness

echo "=== AAX Kubernetes Health Check ==="
kubectl get pods -n aax -o wide --no-headers | while read pod ns rest; do
    ready=$(kubectl get pod "$pod" -n aax -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
    echo "$pod: Ready=$ready"
done
```

---

## Alert Thresholds

| Metric                     | Warning | Critical       |
| -------------------------- | ------- | -------------- |
| Health check response time | > 5s    | > 10s          |
| Failed health checks       | 1       | 2+ consecutive |
| Pod restart count          | > 5     | > 10           |
| CPU usage                  | > 80%   | > 95%          |
| Memory usage               | > 80%   | > 95%          |
| Disk usage                 | > 80%   | > 95%          |

---

## Related Documentation

- [Monitoring](./MONITORING.md) - Detailed monitoring guide
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues and solutions
