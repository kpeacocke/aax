# Event-Driven Ansible Controller

Event-Driven Ansible (EDA) controller provides a scalable means of integrating disparate sources of events through a single unified platform and acting on those events by using rulebooks.

This directory contains the Docker configuration for running EDA with ansible-rulebook.

## Overview

The Event-Driven Ansible controller enables:

- **Event Source Integration** - Connect to webhooks, monitoring systems, APIs, and event streams
- **Rulebook Execution** - Define automation rules that trigger on events
- **Automated Response** - Execute actions through Automation Controller when events occur
- **Real-time Processing** - Low-latency event processing and automation
- **Scalable Architecture** - Distributed event processing across multiple workers

## Architecture

### Components

- **EDA Controller** - Central event processing engine running ansible-rulebook
- **PostgreSQL** - Event data and rulebook storage
- **Redis** - Message queuing for event processing
- **API Server** - REST API for rulebook management and event submission

### Event Flow

```text
Event Sources
    ↓
  Webhook
    ↓
EDA Controller (ansible-rulebook)
    ↓
Rulebook Processing
    ↓
Action (Call Automation Controller)
    ↓
Ansible Execution
```

## Quick Start

### Prerequisites

1. Docker Engine 20.10 or later
2. Docker Compose 5.1.0 or later
3. AAX core services available (optional, for integration)

### 1. Configure Environment Variables

```bash
cd /workspaces/aax
cp .env.example .env

# Add EDA configuration to .env
cat >> .env <<EOF
# Event-Driven Ansible Configuration
EDA_DB_NAME=eda
EDA_DB_USER=eda
EDA_DB_PASSWORD=edapass
EDA_LOG_LEVEL=INFO
EOF
```

### 2. Start EDA Services

```bash
# Start only EDA
docker compose -f docker-compose.eda.yml --profile eda up -d

# Or start with all services
docker compose -f docker-compose.yml -f docker-compose.eda.yml --profile eda up -d
```

### 3. Verify Services are Running

```bash
# Check service status
docker compose -f docker-compose.eda.yml ps

# Check EDA health
curl http://localhost:5000/health

# View logs
docker compose -f docker-compose.eda.yml logs -f eda-controller
```

### 4. Access EDA API

```bash
# Get API documentation
curl http://localhost:5000/openapi.json

# Create a test rulebook
curl -X POST http://localhost:5000/api/v1/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-ruleset",
    "description": "Test ruleset",
    "rules": []
  }'
```

## Configuration

### Environment Variables

| Variable           | Default        | Description                |
| ------------------ | -------------- | -------------------------- |
| `EDA_DB_HOST`      | `eda-postgres` | PostgreSQL host            |
| `EDA_DB_PORT`      | `5432`         | PostgreSQL port            |
| `EDA_DB_NAME`      | `eda`          | Database name              |
| `EDA_DB_USER`      | `eda`          | Database user              |
| `EDA_DB_PASSWORD`  | `edapass`      | Database password          |
| `EDA_REDIS_HOST`   | `eda-redis`    | Redis host                 |
| `EDA_REDIS_PORT`   | `6379`         | Redis port                 |
| `EDA_PORT`         | `5000`         | API port                   |
| `EDA_HOST`         | `0.0.0.0`      | API host                   |
| `EDA_LOG_LEVEL`    | `INFO`         | Logging level              |
| `EDA_SKIP_DB_WAIT` | `false`        | Skip database startup wait |

### Docker Compose Configuration

Default configuration in `docker-compose.eda.yml`:

```yaml
eda-controller:
  image: aax/eda-controller:latest
  ports:
    - "5000:5000"
  environment:
    EDA_DB_HOST: eda-postgres
    EDA_DB_PORT: 5432
    EDA_DB_NAME: eda
    EDA_DB_USER: eda
    EDA_DB_PASSWORD: edapass
    EDA_REDIS_HOST: eda-redis
    EDA_REDIS_PORT: 6379
    EDA_LOG_LEVEL: INFO
  depends_on:
    - eda-postgres
    - eda-redis
  volumes:
    - eda_projects:/home/eda/projects
    - eda_logs:/var/log/eda
```

## Rulebook Examples

### Basic Webhook Rulebook

**`rulebooks/webhook-example.yml`**

```yaml
---
- name: Listen for webhooks and trigger AWX jobs
  hosts: localhost
  sources:
    - name: listen
      ansible.eda.webhook:
        host: 0.0.0.0
        port: 5001

  rules:
    - name: Run AWX job on webhook
      condition: event.payload.action == "deploy"
      action:
        run_playbook:
          name: run_awx_tower_job_template.yml
          extra_vars:
            awx_host: "{{ awx_host }}"
            awx_token: "{{ awx_token }}"
            job_template_id: "{{ job_template_id }}"
            extra_vars: "{{ event.payload.extra_vars }}"
```

### Monitoring Alert Rulebook

**`rulebooks/monitoring-example.yml`**

```yaml
---
- name: Listen for Prometheus alerts
  hosts: localhost
  sources:
    - name: alerts
      ansible.eda.extension:
        plugin: alertmanager_receiver
        host: 0.0.0.0
        port: 5002

  rules:
    - name: High CPU Usage
      condition: event.alert.labels.severity == "critical" and "high_cpu" in event.alert.labels.alertname
      action:
        run_playbook:
          name: remediate_high_cpu.yml
          extra_vars:
            instance: "{{ event.alert.labels.instance }}"
            severity: "{{ event.alert.labels.severity }}"

    - name: Service Down
      condition: event.alert.labels.alertname == "ServiceDown"
      action:
        debug:
          msg: "Service {{ event.alert.labels.service }} is down"
```

### GitHub Webhook Rulebook

**`rulebooks/github-example.yml`**

```yaml
---
- name: GitHub event automation
  hosts: localhost
  sources:
    - name: github
      ansible.eda.webhook:
        host: 0.0.0.0
        port: 5003

  rules:
    - name: Run tests on push
      condition: event.body.action == "push" and event.body.ref == "refs/heads/main"
      action:
        run_playbook:
          name: run_ci_tests.yml
          extra_vars:
            repo: "{{ event.body.repository.full_name }}"
            sha: "{{ event.body.after }}"

    - name: Deploy on release
      condition: event.body.action == "released"
      action:
        run_playbook:
          name: deploy_release.yml
          extra_vars:
            version: "{{ event.body.release.tag_name }}"
            assets: "{{ event.body.release.assets }}"
```

## Integration with Automation Controller

### Submit Events to EDA

```bash
# Submit a webhook event
curl -X POST http://localhost:5000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "source": "webhook",
    "payload": {
      "action": "deploy",
      "environment": "production",
      "version": "1.2.3"
    }
  }'
```

### Trigger AWX Job from EDA

**`playbooks/run_awx_tower_job_template.yml`**

```yaml
---
- name: Run AWX Job Template
  hosts: localhost
  gather_facts: no
  vars:
    awx_host: "{{ awx_host | default('http://localhost:8080') }}"
    awx_token: "{{ awx_token }}"
    job_template_id: "{{ job_template_id }}"
    extra_vars: {}

  tasks:
    - name: Launch AWX job
      awx.awx.job_launch:
        job_template: "{{ job_template_id }}"
        extra_vars: "{{ extra_vars }}"
        controller_host: "{{ awx_host }}"
        controller_oauthtoken: "{{ awx_token }}"
      register: launch_result

    - name: Wait for job completion
      awx.awx.job_wait:
        job_id: "{{ launch_result.id }}"
        controller_host: "{{ awx_host }}"
        controller_oauthtoken: "{{ awx_token }}"
      register: job_result

    - name: Report result
      debug:
        msg: "Job {{ job_result.id }} completed with status {{ job_result.status }}"
```

## API Endpoints

### Rulebook Management

```bash
# List rulesets
curl http://localhost:5000/api/v1/rulesets

# Create ruleset
curl -X POST http://localhost:5000/api/v1/rulesets \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "rules": []}'

# Get ruleset
curl http://localhost:5000/api/v1/rulesets/1

# Update ruleset
curl -X PUT http://localhost:5000/api/v1/rulesets/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "updated", "rules": []}'

# Delete ruleset
curl -X DELETE http://localhost:5000/api/v1/rulesets/1
```

### Event Management

```bash
# Submit event
curl -X POST http://localhost:5000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"source": "webhook", "payload": {}}'

# Get events
curl http://localhost:5000/api/v1/events

# Get event history
curl http://localhost:5000/api/v1/events?limit=100&offset=0
```

### Activation Management

```bash
# List activations
curl http://localhost:5000/api/v1/activations

# Activate ruleset
curl -X POST http://localhost:5000/api/v1/activations \
  -H "Content-Type: application/json" \
  -d '{"ruleset_id": 1}'

# Get activation status
curl http://localhost:5000/api/v1/activations/1

# Stop activation
curl -X DELETE http://localhost:5000/api/v1/activations/1
```

## Logging & Troubleshooting

### View Logs

```bash
# EDA Controller logs
docker compose -f docker-compose.eda.yml logs -f eda-controller

# PostgreSQL logs
docker compose -f docker-compose.eda.yml logs -f eda-postgres

# Redis logs
docker compose -f docker-compose.eda.yml logs -f eda-redis

# All services
docker compose -f docker-compose.eda.yml logs -f
```

### Enable Debug Logging

```bash
# Update log level
export EDA_LOG_LEVEL=DEBUG

# Restart service
docker compose -f docker-compose.eda.yml restart eda-controller

# View debug logs
docker compose -f docker-compose.eda.yml logs -f eda-controller
```

### Common Issues

| Issue                            | Solution                                               |
| -------------------------------- | ------------------------------------------------------ |
| Connection refused to PostgreSQL | Check eda-postgres is running; verify credentials      |
| Redis connection error           | Verify eda-redis is running and accessible             |
| Rulebook not executing           | Check ruleset is activated; review logs for errors     |
| Webhook not triggering           | Verify webhook URL and payload format                  |
| High latency                     | Check Redis memory usage; optimize rulebook complexity |

## Performance Tuning

### Scale Workers

```bash
# Increase worker processes
docker compose -f docker-compose.eda.yml up -d \
  --scale eda-worker=3
```

### Optimize Database

```bash
# Check query performance
docker exec eda-postgres psql -U eda -d eda \
  -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Add indexes
docker exec eda-postgres psql -U eda -d eda \
  -c "CREATE INDEX IF NOT EXISTS events_source_idx ON events(source);"
```

### Redis Optimization

```bash
# Check memory usage
docker exec eda-redis redis-cli info memory

# Configure persistence
docker exec eda-redis redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

## Building Custom Rulebooks

### Rulebook Components

- **Sources** - Event sources (webhooks, APIs, monitoring systems)
- **Conditions** - Trigger conditions (event matching/filtering)
- **Actions** - Response actions (run playbooks, webhooks, notifications)

### Custom Source Plugin

**`plugins/event_sources/custom_source.py`**

```python
import asyncio
from typing import Any, AsyncGenerator

async def main(
    name: str,
    host: str = "0.0.0.0",
    port: int = 5001,
    **kwargs: Any
) -> AsyncGenerator[dict, None]:
    """
    Custom event source.

    Args:
        name: Source name
        host: Listen host
        port: Listen port
    """
    # Implementation of event source
    yield {"source": name, "payload": {}}
```

## References

- [Event-Driven Ansible Documentation](https://ansible.readthedocs.io/projects/rulebook/)
- [ansible-rulebook GitHub](https://github.com/ansible/ansible-rulebook)
- [AWX Integration Guide](../../controller/CONTROLLER.md)
- [Ansible Content Collections](https://galaxy.ansible.com/)

---

**Last Updated:** February 27, 2026  
**EDA Version:** 1.1.3  
**Status:** Production-ready
