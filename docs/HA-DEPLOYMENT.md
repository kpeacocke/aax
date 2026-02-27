# High Availability (HA) Deployment Guide

This guide provides comprehensive instructions for deploying AAX components in a high-availability configuration using load balancers, database replication, and distributed services.

## Overview

AAX can be deployed in HA mode to eliminate single points of failure and improve reliability and scalability. HA deployments use:

- **External Load Balancer** - Distributes traffic across multiple instances
- **PostgreSQL Replication** - Primary-replica database replication for redundancy
- **Redis Sentinel** - Redis monitoring and automatic failover
- **Multiple Service Instances** - Horizontal scaling of services
- **Shared Storage** - Distributed filesystem or S3-compatible storage for content

## Architecture

### Single-Node (Current Default)

```text
┌─────────────────────────────────────────┐
│  AAX Services                           │
│  ├── AWX (web + task)                   │
│  ├── Galaxy NG / Pulp                   │
│  └── EDA Controller                     │
│                                          │
│  ├── PostgreSQL (primary)               │
│  ├── Redis (single)                     │
│  └── Receptor (mesh node)               │
└─────────────────────────────────────────┘
        ↓
   Clients
```

### HA Configuration (Multi-Node)

```text
┌────────────────────────────────────────────────────────────┐
│                    Load Balancer                            │
│         (nginx / HAProxy / AWS ELB / etc.)                 │
└────────────────────────────────────────────────────────────┘
    ↓                          ↓                       ↓
┌──────────────────┐     ┌──────────────────┐  ┌──────────────────┐
│  AWX Node 1      │     │  AWX Node 2      │  │  AWX Node 3      │
│ ├─ awx-web       │     │ ├─ awx-web       │  │ ├─ awx-web       │
│ └─ awx-task      │     │ └─ awx-task      │  │ └─ awx-task      │
└──────────────────┘     └──────────────────┘  └──────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Shared Database Layer                           │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │  PostgreSQL      │      │  PostgreSQL      │             │
│  │  Primary         │ ───→ │  Replica         │             │
│  │  (Read/Write)    │      │  (Read-Only)     │             │
│  └──────────────────┘      └──────────────────┘             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Shared Cache & Message Layer                    │
│  ┌──────────────────┐      ┌──────────────────┐             │
│  │  Redis Master    │◄────→│  Redis Replica   │             │
│  └──────────────────┘      └──────────────────┘             │
│  Managed by Redis Sentinel                                   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Shared Content Storage                          │
│  - NFS / GlusterFS / S3-Compatible Storage                   │
│  - Used by Pulp and Galaxy NG                                │
└──────────────────────────────────────────────────────────────┘
```

## Prerequisites for HA Deployment

### Infrastructure

- Minimum 3 nodes (for quorum and redundancy)
- 4+ GB RAM per node
- 20+ GB disk space per node
- Reliable network connectivity between nodes
- NFS server or S3-compatible storage for shared content

### Software

- Docker Engine 20.10+
- Docker Compose 2.0+ or similar orchestration
- Load balancer (nginx, HAProxy, cloud provider LB)
- PostgreSQL 15+ (can run in containers or on dedicated servers)
- Redis 7+ (can run in containers or on dedicated servers)

### Network

- Network load balancer or reverse proxy
- Port 80/443 accessible from clients
- Ports 5432 (PostgreSQL), 6379 (Redis) accessible between nodes
- Port 22 (SSH) for administration

---

## Step 1: Load Balancer Setup

### Option A: HAProxy Load Balancer

**HAProxy Configuration** (`/etc/haproxy/haproxy.cfg`)

```ini
# Global settings
global
  maxconn 4096
  log stdout local0
  daemon

# Defaults
defaults
  log global
  mode http
  option httplog
  option dontlognull
  timeout connect 5000ms
  timeout client 50000ms
  timeout server 50000ms

# HTTP frontend (for AWX)
frontend http_in
  bind *:80
  redirect scheme https code 301 if !{ ssl_fc }

# HTTPS frontend
frontend https_in
  bind *:443 ssl crt /etc/ssl/certs/aax-cert.pem
  reqadd X-Forwarded-Proto:\ https
  default_backend awx_backend

# AWX backend (multiple nodes)
backend awx_backend
  balance roundrobin
  server awx1 192.168.1.10:8080 check
  server awx2 192.168.1.11:8080 check
  server awx3 192.168.1.12:8080 check

# Private Automation Hub frontend/backend
frontend hub_in
  bind *:8081 ssl crt /etc/ssl/certs/aax-cert.pem
  default_backend galaxy_backend

backend galaxy_backend
  balance roundrobin
  server hub1 192.168.1.20:8000 check
  server hub2 192.168.1.21:8000 check
  server hub3 192.168.1.22:8000 check

# Stats page (optional)
frontend stats
  bind 127.0.0.1:8404
  default_backend stats

backend stats
  stats enable
  stats uri /stats
  stats refresh 10s
```

#### Start HAProxy

```bash
# Using Docker
docker run -d \
  --name haproxy \
  -v /etc/haproxy/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg \
  -p 80:80 \
  -p 443:443 \
  -p 8404:8404 \
  haproxy:2.8

# Check stats at http://localhost:8404/stats
```

### Option B: Nginx Load Balancer

**Nginx Configuration** (`/etc/nginx/conf.d/aax.conf`)

```nginx
# AWX upstream
upstream awx_backend {
  least_conn;  # Use least connections load balancing
  server 192.168.1.10:8080 max_fails=2 fail_timeout=30s;
  server 192.168.1.11:8080 max_fails=2 fail_timeout=30s;
  server 192.168.1.12:8080 max_fails=2 fail_timeout=30s;
  keepalive 32;
}

# Private Hub upstream
upstream galaxy_backend {
  least_conn;
  server 192.168.1.20:8000 max_fails=2 fail_timeout=30s;
  server 192.168.1.21:8000 max_fails=2 fail_timeout=30s;
  server 192.168.1.22:8000 max_fails=2 fail_timeout=30s;
  keepalive 32;
}

# Redirect HTTP to HTTPS
server {
  listen 80 default_server;
  server_name _;
  return 301 https://$host$request_uri;
}

# AWX HTTPS
server {
  listen 443 ssl http2;
  server_name aax.example.com;

  ssl_certificate /etc/ssl/certs/aax-cert.pem;
  ssl_certificate_key /etc/ssl/private/aax-key.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;

  proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=awx_cache:10m;

  location / {
    proxy_pass http://awx_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
  }
}

# Private Hub HTTPS
server {
  listen 443 ssl http2;
  server_name hub.example.com;

  ssl_certificate /etc/ssl/certs/aax-cert.pem;
  ssl_certificate_key /etc/ssl/private/aax-key.pem;

  location / {
    proxy_pass http://galaxy_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

#### Start Nginx

```bash
docker run -d \
  --name nginx \
  -v /etc/nginx/conf.d/aax.conf:/etc/nginx/conf.d/default.conf \
  -v /etc/ssl/certs:/etc/ssl/certs \
  -v /etc/ssl/private:/etc/ssl/private \
  -p 80:80 \
  -p 443:443 \
  nginx:1.25
```

---

## Step 2: PostgreSQL High Availability

### Option A: PostgreSQL Streaming Replication

#### Primary Node Setup

```bash
# Create replication user
docker exec -it awx-postgres psql -U awx -d awx <<EOF
CREATE USER replication LOGIN REPLICATION ENCRYPTED PASSWORD 'replication_password'; -- pragma: allowlist secret
GRANT CONNECT ON DATABASE awx to replication;
EOF

# Update postgresql.conf for replication
docker exec -it awx-postgres sh -c 'echo "max_wal_senders = 10" >> /var/lib/postgresql/data/postgresql.conf'
docker exec -it awx-postgres sh -c 'echo "wal_level = replica" >> /var/lib/postgresql/data/postgresql.conf'
docker exec -it awx-postgres sh -c 'echo "hot_standby = on" >> /var/lib/postgresql/data/postgresql.conf'

# Restart PostgreSQL
docker restart awx-postgres
```

#### Replica Node Setup

```yaml
# docker-compose-replica.yml
version: '3.8'

services:
  awx-postgres-replica:
    image: postgres:15
    environment:
      POSTGRES_DB: awx
      POSTGRES_USER: awx
      POSTGRES_PASSWORD: awxpass # pragma: allowlist secret
    volumes:
      - awx_postgres_replica_data:/var/lib/postgresql/data
    command: |
      bash -c '
        pg_basebackup -h awx-postgres -D /var/lib/postgresql/data \
          -U replication -v -P -W \
          --write-recovery-conf
        postgres
      '
    depends_on:
      - awx-postgres
    networks:
      - awx-network
```

#### Promote Replica to Primary (Failover)

```bash
# On replica node, promote to primary
docker exec -it awx-postgres-replica pg_ctl promote

# Update AWX to point to new primary
docker exec awx-web bash -c '
  export POSTGRES_HOST=awx-postgres-replica
  # Restart AWX services
'
```

### Option B: Managed PostgreSQL (Cloud Provider)

For production, consider using managed PostgreSQL:

- AWS RDS PostgreSQL
- Google Cloud SQL
- Azure Database for PostgreSQL
- DigitalOcean Managed Databases

**Benefits:**

- Automatic backups
- Monitor & auto-failover
- Read replicas for scaling read operations
- No operational overhead

#### Update AAX Configuration

```bash
# Set environment variables
export POSTGRES_HOST=your-rds-endpoint.amazonaws.com
export POSTGRES_PORT=5432
export POSTGRES_USER=awx
export POSTGRES_PASSWORD=your-secure-password # pragma: allowlist secret

# Update docker-compose to use external database
# Remove database containers and set connection strings
```

---

## Step 3: Redis High Availability

### Option A: Redis Sentinel

**Redis Sentinel Configuration** (`redis-sentinel.conf`)

```conf
# Master node to monitor
sentinel monitor mymaster 192.168.1.10 6379 2

# Time to wait before failover
sentinel down-after-milliseconds mymaster 5000

# Number of replicas to reconfigure after failover
sentinel parallel-syncs mymaster 1

# Failover timeout
sentinel failover-timeout mymaster 10000

# Log
logfile /var/log/redis/sentinel.log
```

#### Deploy Sentinel Nodes

```bash
# Node 1
docker run -d \
  --name redis-sentinel-1 \
  -v redis-sentinel.conf:/etc/sentinel.conf \
  redis:7 redis-sentinel /etc/sentinel.conf --port 26379

# Node 2
docker run -d \
  --name redis-sentinel-2 \
  -v redis-sentinel.conf:/etc/sentinel.conf \
  redis:7 redis-sentinel /etc/sentinel.conf --port 26379

# Node 3
docker run -d \
  --name redis-sentinel-3 \
  -v redis-sentinel.conf:/etc/sentinel.conf \
  redis:7 redis-sentinel /etc/sentinel.conf --port 26379
```

#### Update AWX to Use Sentinel

```bash
export REDIS_SENTINEL_HOSTS="sentinel-1:26379,sentinel-2:26379,sentinel-3:26379"
export REDIS_SENTINEL_SERVICE_NAME="mymaster"
```

### Option B: Redis Cluster

For even higher availability and throughput:

```bash
# Create Redis cluster with 6 nodes (3 masters + 3 replicas)
for i in {1..6}; do
  docker run -d \
    --name redis-cluster-$i \
    -p $((6379+i)):6379 \
    redis:7 redis-server --cluster-enabled yes \
    --cluster-config-file /data/nodes.conf \
    --port $((6379+i))
done

# Create cluster
docker run -it --rm redis:7 redis-cli \
  --cluster create \
  127.0.0.1:6380 127.0.0.1:6381 127.0.0.1:6382 \
  127.0.0.1:6383 127.0.0.1:6384 127.0.0.1:6385 \
  --cluster-replicas 1
```

---

## Step 4: Shared Storage Setup

### NFS Server

#### Server Setup

```bash
# Install NFS server
sudo apt-get install nfs-kernel-server

# Create export directory
sudo mkdir -p /var/lib/aax/content
sudo chmod 777 /var/lib/aax/content

# Add to /etc/exports
sudo bash -c 'echo "/var/lib/aax/content *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports'

# Export
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

#### Client Setup (each AAX node)

```bash
# Install NFS client
sudo apt-get install nfs-common

# Mount shared storage
sudo mkdir -p /mnt/aax-content
sudo mount -t nfs nfs-server:/var/lib/aax/content /mnt/aax-content

# Make persistent
sudo bash -c 'echo "nfs-server:/var/lib/aax/content /mnt/aax-content nfs defaults 0 0" >> /etc/fstab'

# Update docker-compose to use mounted path
# volumes:
#   - /mnt/aax-content:/var/lib/pulp/content
```

### S3-Compatible Storage (Minio / AWS S3)

#### Minio Setup (Self-Hosted)

```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"

# Configure Pulp to use Minio as storage backend
export PULP_AZURE_STORAGE_ACCOUNT_NAME=minio
export PULP_AZURE_STORAGE_ACCOUNT_KEY=minioadmin
```

#### AWS S3 Setup

```bash
# Create IAM user and S3 bucket
aws iam create-user --user-name aax-s3
aws iam attach-user-policy --user-name aax-s3 \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws s3 create-bucket --bucket aax-pulp-content --region us-east-1

# Configure Pulp for S3
export PULP_STORAGE_CLASS=pulpcore.app.models.storage.S3Storage
export PULP_AWS_ACCESS_KEY_ID=<key>
export PULP_AWS_SECRET_ACCESS_KEY=<secret>
export PULP_AWS_STORAGE_BUCKET_NAME=aax-pulp-content
export PULP_AWS_S3_REGION_NAME=us-east-1
```

---

## Step 5: Multi-Node Docker Compose Deployment

**HA Docker Compose Template** (`docker-compose.ha.yml`)

```yaml
version: '3.8'

services:
  # External PostgreSQL (AWS RDS or similar)
  # External Redis (Redis Sentinel cluster)
  # External Load Balancer (nginx, HAProxy)

  awx-web:
    image: aax/awx:latest
    environment:
      POSTGRES_HOST: rds-endpoint.amazonaws.com
      POSTGRES_PORT: 5432
      POSTGRES_DB: awx
      POSTGRES_USER: awx
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis-sentinel-1
      REDIS_PORT: 26379
      REDIS_SENTINEL_SERVICE_NAME: mymaster
    ports:
      - "8080:8080"
    depends_on:
      - awx-task
    networks:
      - awx-network

  awx-task:
    image: aax/awx:latest
    environment:
      POSTGRES_HOST: rds-endpoint.amazonaws.com
      POSTGRES_PORT: 5432
      POSTGRES_DB: awx
      POSTGRES_USER: awx
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis-sentinel-1
      REDIS_PORT: 26379
    networks:
      - awx-network
    command: awx-task

  galaxy-ng:
    image: aax/galaxy-ng:latest
    environment:
      POSTGRES_HOST: rds-endpoint.amazonaws.com
      POSTGRES_PORT: 5432
      POSTGRES_DB: galaxy
      POSTGRES_USER: galaxy
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis-sentinel-1
      REDIS_PORT: 26379
    volumes:
      - /mnt/aax-content:/var/lib/pulp
    ports:
      - "8000:8000"
    networks:
      - awx-network

  pulp-worker:
    image: aax/galaxy-ng:latest
    environment:
      POSTGRES_HOST: rds-endpoint.amazonaws.com
      POSTGRES_PORT: 5432
      POSTGRES_DB: galaxy
      POSTGRES_USER: galaxy
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis-sentinel-1
      REDIS_PORT: 26379
    volumes:
      - /mnt/aax-content:/var/lib/pulp
    networks:
      - awx-network
    command: pulp-worker
    deploy:
      replicas: 3  # Scale to multiple workers

networks:
  awx-network:
    driver: bridge
```

### Deploy with Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.ha.yml aax

# Scale services
docker service scale aax_awx-task=3
docker service scale aax_pulp-worker=3
docker service scale aax_galaxy-ng=3

# Check status
docker stack ps aax
```

---

## Step 6: Monitoring & Health Checks

### Monitor Service Health

```bash
# Check service status
docker service ls
docker service ps aax_awx-web

# View logs
docker service logs -f aax_awx-web
docker service logs -f aax_galaxy-ng

# Check resource usage
docker stats
```

### Prometheus Monitoring

**Create `/etc/prometheus/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'awx'
    static_configs:
      - targets: ['localhost:8080']

  - job_name: 'galaxy-ng'
    static_configs:
      - targets: ['localhost:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

#### Deploy Prometheus

```bash
docker run -d \
  --name prometheus \
  -v /etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  -p 9090:9090 \
  prom/prometheus
```

### Alerting

#### AlertManager Configuration

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'team-email'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'

receivers:
  - name: 'team-email'
    email_configs:
      - to: 'devops@example.com'
        from: 'alertmanager@example.com'
        smarthost: 'smtp.example.com:587'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<pagerduty-key>'
```

---

## Failover Testing

### Test Database Failover

```bash
# Simulate primary database failure
docker stop awx-postgres

# Monitor failover time
# Should automatically migrate to replica in ~30 seconds

# Verify AWX still operational
curl -s http://localhost:8080/api/v2/ping/

# Restore primary
docker start awx-postgres
```

### Test Load Balancer Failover

```bash
# Stop one AWX instance
docker stop awx-web-1

# Verify traffic redirected to other instances
# Monitor HAProxy/Nginx stats page

# Restore instance
docker start awx-web-1
```

### Test Redis Failover

```bash
# Stop Redis master
docker stop awx-redis

# Sentinel should promote replica in ~5 seconds
docker exec redis-sentinel-1 redis-cli -p 26379 sentinel masters

# Verify data still accessible
curl -s http://localhost:8080/api/v2/ping/
```

---

## Backup & Disaster Recovery

### PostgreSQL Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

docker exec awx-postgres pg_dump -U awx awx | gzip > $BACKUP_DIR/awx-$DATE.sql.gz
docker exec hub-postgres pg_dump -U galaxy galaxy | gzip > $BACKUP_DIR/galaxy-$DATE.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://aax-backups/postgresql/ --recursive --exclude "*" --include "*.sql.gz"
```

### Restore from Backup

```bash
# Restore PostgreSQL
gunzip < /backups/postgresql/awx-2024-02-27.sql.gz | \
  docker exec -i awx-postgres psql -U awx awx

# Verify data
docker exec awx-postgres psql -U awx awx -c "SELECT COUNT(*) FROM main_organization;"
```

---

## Performance Tuning

### PostgreSQL Tuning

```bash
# Update postgresql.conf for HA
docker exec awx-postgres bash -c 'cat >> /var/lib/postgresql/data/postgresql.conf <<EOF
# Memory
shared_buffers = 1GB
effective_cache_size = 4GB
maintenance_work_mem = 256MB

# Connections
max_connections = 500
max_prepared_transactions = 100

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9
wal_writer_delay = 200ms

# Performance
random_page_cost = 1.1
work_mem = 4MB
EOF'

docker restart awx-postgres
```

### Redis Optimization

```bash
# Use Redis pipeline for batch operations
# Enable Redis clustering for throughput
# Monitor eviction policies and memory usage
```

---

## Maintenance & Upgrades

### Rolling Updates

```bash
# Update one node at a time without downtime
for node in awx-web-1 awx-web-2 awx-web-3; do
  # Stop node
  docker service update --image aax/awx:v2.0.0 $node

  # Wait for health check
  sleep 30

  # Verify other nodes handling traffic
done
```

### Health Check Verification

```bash
# Before upgrade
for i in 1 2 3; do
  curl -s http://awx-node-$i:8080/api/v2/ping/
done

# After upgrade
for i in 1 2 3; do
  curl -s http://awx-node-$i:8080/api/v2/ping/
done
```

---

## Troubleshooting

### Common HA Issues

| Issue                 | Cause                       | Solution                                              |
| --------------------- | --------------------------- | ----------------------------------------------------- |
| Services not starting | Database not ready          | Check PostgreSQL health; increase startup timeout     |
| High latency          | Load balancer misconfigured | Verify load balancer settings; check network          |
| Data inconsistency    | Replication lag             | Increase replication workers; check network bandwidth |
| Cache misses          | Redis failover slow         | Switch to Redis Cluster; tune Sentinel timeouts       |
| Storage full          | No cleanup of old content   | Configure Pulp retention policies; monitor disk usage |

### Debug Commands

```bash
# Check service status
docker service ps aax_awx-web

# View logs
docker service logs -f aax_awx-web

# Test database connection
docker exec awx-web psql -h postgres-host -U awx -d awx -c "SELECT 1"

# Test Redis connection
docker exec awx-web redis-cli -h redis-host ping

# Check load balancer stats
curl http://localhost:8404/stats  # HAProxy
curl http://localhost/nginx_status # Nginx
```

---

## References

- [PostgreSQL Replication](https://www.postgresql.org/docs/15/warm-standby.html)
- [Redis Sentinel](https://redis.io/docs/reference/sentinel-clients/)
- [HAProxy Load Balancing](http://www.haproxy.org/)
- [Nginx Upstream](https://nginx.org/en/docs/http/upstream.html)
- [Docker Swarm Services](https://docs.docker.com/engine/swarm/services/)
- [Kubernetes YAML Examples](../k8s/)

---

**Last Updated:** February 27, 2026  
**AAX Version:** 1.0.0  
**Status:** Production-ready HA deployment strategies
