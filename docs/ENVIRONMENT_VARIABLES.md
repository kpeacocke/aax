# Environment Variables Reference

Complete guide to configurable environment variables for AAX deployment.

## AWX Configuration

### Authentication & Security

| Variable             | Default                    | Description                          |
| -------------------- | -------------------------- | ------------------------------------ |
| `AWX_ADMIN_USER`     | `admin`                    | AWX admin username                   |
| `AWX_ADMIN_PASSWORD` | `awxadmin`                 | **Change in production**             |
| `AWX_SECRET_KEY`     | `awxsecret`                | Django secret key for session/crypto |
| `INSIGHTS_URL_BASE`  | `https://cloud.redhat.com` | Red Hat Insights integration URL     |

**⚠️ Security Best Practices:**

```bash
# Generate secure secret keys
openssl rand -hex 32

# Set secure passwords
AWX_ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

### Database Configuration

| Variable            | Default    | Description                                                                   |
| ------------------- | ---------- | ----------------------------------------------------------------------------- |
| `DATABASE_HOST`     | `postgres` | PostgreSQL hostname                                                           |
| `DATABASE_NAME`     | `awx`      | Database name                                                                 |
| `DATABASE_USER`     | `awx`      | Database user                                                                 |
| `DATABASE_PASSWORD` | `awxdb`    | Database password                                                             |
| `DATABASE_PORT`     | `5432`     | PostgreSQL port                                                               |
| `DATABASE_SSLMODE`  | `prefer`   | SSL mode: `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full` |

---

### Email Configuration

| Variable              | Default                 | Description                          |
| --------------------- | ----------------------- | ------------------------------------ |
| `EMAIL_HOST`          | `localhost`             | SMTP server hostname                 |
| `EMAIL_PORT`          | `25`                    | SMTP port (587 for TLS, 465 for SSL) |
| `EMAIL_HOST_USER`     | ``                      | SMTP username                        |
| `EMAIL_HOST_PASSWORD` | ``                      | SMTP password                        |
| `EMAIL_USE_TLS`       | `False`                 | Enable TLS encryption                |
| `EMAIL_USE_SSL`       | `False`                 | Enable SSL encryption                |
| `EMAIL_TIMEOUT`       | `10`                    | Connection timeout in seconds        |
| `SERVER_EMAIL`        | `root@example.com`      | From address for system emails       |
| `DEFAULT_FROM_EMAIL`  | `webmaster@example.com` | Default From header                  |

**Example - Gmail:**

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
```

---

### LDAP/ActiveDirectory Integration

| Variable                        | Default                      | Description                                      |
| ------------------------------- | ---------------------------- | ------------------------------------------------ |
| `AUTH_LDAP_SERVER_URI`          | ``                           | LDAP server URL, e.g., `ldap://ldap.example.com` |
| `AUTH_LDAP_BIND_DN`             | ``                           | Bind user DN                                     |
| `AUTH_LDAP_BIND_PASSWORD`       | ``                           | Bind user password                               |
| `AUTH_LDAP_USER_SEARCH_BASE`    | ``                           | User search base DN                              |
| `AUTH_LDAP_USER_SEARCH_FILTER`  | `(uid=%(user)s)`             | User search filter                               |
| `AUTH_LDAP_GROUP_SEARCH_BASE`   | ``                           | Group search base DN                             |
| `AUTH_LDAP_GROUP_SEARCH_FILTER` | `(objectClass=groupOfNames)` | Group search filter                              |

---

### OAuth2 Integration

| Variable                                 | Default | Description                 |
| ---------------------------------------- | ------- | --------------------------- |
| `SOCIAL_AUTH_GITHUB_CALLBACK_URL`        | ``      | GitHub callback URL         |
| `SOCIAL_AUTH_GITHUB_KEY`                 | ``      | GitHub OAuth2 app ID        |
| `SOCIAL_AUTH_GITHUB_SECRET`              | ``      | GitHub OAuth2 app secret    |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_CALLBACK_URL` | ``      | Google callback URL         |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY`          | ``      | Google OAuth2 client ID     |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET`       | ``      | Google OAuth2 client secret |

---

### Logging & Monitoring

| Variable                  | Default             | Description                                                    |
| ------------------------- | ------------------- | -------------------------------------------------------------- |
| `LOG_LEVEL`               | `INFO`              | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_AGGREGATOR_HOST`     | ``                  | Syslog aggregator hostname                                     |
| `LOG_AGGREGATOR_PORT`     | `514`               | Syslog aggregator port                                         |
| `LOG_AGGREGATOR_TYPE`     | `logstash`          | Aggregator type: `logstash`, `splunk`, `sumologic`, `loggly`   |
| `LOG_AGGREGATOR_USERNAME` | ``                  | Aggregator username                                            |
| `LOG_AGGREGATOR_PASSWORD` | ``                  | Aggregator password                                            |
| `LOG_AGGREGATOR_LOGGERS`  | `awx,awx.analytics` | Comma-separated logger names                                   |
| `METRICS_ENABLED`         | `True`              | Enable Prometheus metrics                                      |

---

### Performance & Resources

| Variable                            | Default | Description                                |
| ----------------------------------- | ------- | ------------------------------------------ |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | `1000`  | Tasks per worker process before restart    |
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | `4`     | Concurrent tasks per worker                |
| `CELERY_WORKER_HEARTBEAT_FREQUENCY` | `2`     | Worker heartbeat interval (seconds)        |
| `TASK_MANAGER_MEMORY_THRESHOLD`     | `100`   | Memory threshold % before pausing tasks    |
| `CALLBACK_QUEUE_CAPACITY`           | `1000`  | Maximum pending callbacks                  |
| `JOB_RUNTIME_LIMIT`                 | `0`     | Max job runtime in minutes (0 = unlimited) |
| `JOB_EVENT_RETENTION_DAYS`          | `30`    | Days to keep job event logs                |
| `JOB_EVENT_RETENTION_GIGA_BYTES`    | `100`   | Max job event log size in GB               |

---

### Feature Flags

| Variable                        | Default    | Description                       |
| ------------------------------- | ---------- | --------------------------------- |
| `ALLOW_EXTERNAL_ADMIN_CREATION` | `False`    | Allow creating admins via API     |
| `BULK_OPERATION_MAX_SIZE`       | `200`      | Max items in bulk operations      |
| `COLLECTIONS_ENABLED`           | `True`     | Enable Galaxy Collections support |
| `CUSTOM_LOGIN_INFO`             | ``         | Custom login page text            |
| `DISPLAY_LOGIN_ATTEMPT_NUMBERS` | `False`    | Show login attempt count          |
| `INSIGHTS_TRACKING_STATE`       | `True`     | Enable Insights telemetry         |
| `REDACT_SENSITIVE_DATA_IN_LOGS` | `True`     | Remove secrets from logs          |
| `TOWER_URLCONF`                 | `awx.urls` | URL configuration module          |

---

## Database (PostgreSQL)

| Variable               | Default                    | Description                                   |
| ---------------------- | -------------------------- | --------------------------------------------- |
| `POSTGRES_DB`          | `awx`                      | Database name                                 |
| `POSTGRES_USER`        | `awx`                      | Database user                                 |
| `POSTGRES_PASSWORD`    | `awxdb`                    | Database password                             |
| `POSTGRES_INITDB_ARGS` | ``                         | PostgreSQL init args, e.g., `--encoding=UTF8` |
| `PGDATA`               | `/var/lib/postgresql/data` | Data directory                                |

---

## Execution Environments

### Builder

| Variable                  | Default             | Description                    |
| ------------------------- | ------------------- | ------------------------------ |
| `EE_BUILDER_TIMEOUT`      | `3600`              | Build timeout in seconds       |
| `EE_BUILDER_MEMORY`       | `4g`                | Build container memory limit   |
| `EE_BUILDER_WORKDIR`      | `/tmp/ee`           | Build working directory        |
| `ANSIBLE_BUILDER_VERSION` | `(from Dockerfile)` | ansible-builder version to use |

### Runtime

| Variable           | Default              | Description                         |
| ------------------ | -------------------- | ----------------------------------- |
| `EE_DOCKER_IMAGE`  | `aax/ee-base:latest` | Default execution environment image |
| `DEFAULT_EE_IMAGE` | `aax/ee-base:latest` | System default EE image             |
| `EE_PULL_POLICY`   | `if-not-present`     | Image pull policy for EEs           |

---

## Receptor Node

| Variable                       | Default   | Description                  |
| ------------------------------ | --------- | ---------------------------- |
| `RECEPTOR_BIND_ADDRESS`        | `0.0.0.0` | Bind address for Receptor    |
| `RECEPTOR_BIND_PORT`           | `5500`    | Bind port for Receptor       |
| `RECEPTOR_CONNECT_TIMEOUT`     | `10`      | Connection timeout (seconds) |
| `RECEPTOR_FRAMEWORK_LOG_LEVEL` | `info`    | Receptor framework log level |

---

## Galaxy NG

| Variable                   | Default                | Description              |
| -------------------------- | ---------------------- | ------------------------ |
| `GALAXY_DOCKER_IMAGE`      | `aax/galaxy-ng:latest` | Galaxy NG image          |
| `GALAXY_POSTGRES_HOST`     | `postgres`             | Galaxy database host     |
| `GALAXY_POSTGRES_NAME`     | `galaxy`               | Galaxy database name     |
| `GALAXY_POSTGRES_USER`     | `galaxy`               | Galaxy database user     |
| `GALAXY_POSTGRES_PASSWORD` | `galaxydb`             | Galaxy database password |
| `GALAXY_ADMIN_USER`        | `admin`                | Galaxy admin username    |
| `GALAXY_ADMIN_PASSWORD`    | `galaxyadmin`          | Galaxy admin password    |
| `PULP_BASEPATH`            | `/api/galaxy`          | Base API path for Galaxy |

---

## Pulp

| Variable                 | Default            | Description            |
| ------------------------ | ------------------ | ---------------------- |
| `PULP_DOCKER_IMAGE`      | `aax/pulp:latest`  | Pulp image             |
| `PULP_POSTGRES_HOST`     | `postgres`         | Pulp database host     |
| `PULP_POSTGRES_NAME`     | `pulp`             | Pulp database name     |
| `PULP_POSTGRES_USER`     | `pulp`             | Pulp database user     |
| `PULP_POSTGRES_PASSWORD` | `pulpdb`           | Pulp database password |
| `PULP_ADMIN_USERNAME`    | `admin`            | Pulp admin username    |
| `PULP_ADMIN_PASSWORD`    | `pulpadmin`        | Pulp admin password    |
| `PULP_CONTENT_ORIGIN`    | `http://localhost` | Content origin URL     |

---

## EDA Controller

| Variable                     | Default                     | Description                     |
| ---------------------------- | --------------------------- | ------------------------------- |
| `EDA_DOCKER_IMAGE`           | `aax/eda-controller:latest` | EDA Controller image            |
| `EDA_POSTGRES_HOST`          | `postgres`                  | EDA database host               |
| `EDA_POSTGRES_NAME`          | `eda`                       | EDA database name               |
| `EDA_POSTGRES_USER`          | `eda`                       | EDA database user               |
| `EDA_POSTGRES_PASSWORD`      | `edadb`                     | EDA database password           |
| `EDA_ADMIN_USER`             | `admin`                     | EDA admin username              |
| `EDA_ADMIN_PASSWORD`         | `edaadmin`                  | EDA admin password              |
| `EDA_CONTROLLER_LISTEN_PORT` | `8000`                      | Controller port                 |
| `EDA_ANSIBLE_RUNNER_IMAGE`   | `aax/ee-base:latest`        | EDA execution environment image |

---

## Docker Image Tags & Versions

| Variable               | Default  | Description                 |
| ---------------------- | -------- | --------------------------- |
| `AWX_IMAGE_TAG`        | `latest` | AWX Docker image tag        |
| `EE_BASE_IMAGE_TAG`    | `latest` | EE Base Docker image tag    |
| `EE_BUILDER_IMAGE_TAG` | `latest` | EE Builder Docker image tag |
| `POSTGRES_VERSION`     | `13`     | PostgreSQL version          |
| `REDIS_VERSION`        | `7`      | Redis version               |

---

## Networking

| Variable               | Default               | Description                          |
| ---------------------- | --------------------- | ------------------------------------ |
| `ALLOWED_HOSTS`        | `localhost,127.0.0.1` | Comma-separated allowed hosts        |
| `CSRF_TRUSTED_ORIGINS` | ``                    | Comma-separated CSRF-trusted origins |
| `AWX_HTTPS_BIND_PORT`  | `8443`                | HTTPS port                           |
| `AWX_HTTP_BIND_PORT`   | `8080`                | HTTP port                            |
| `AWX_BIND_ADDRESS`     | `0.0.0.0`             | AWX bind address                     |

**Example - Production HTTPS:**

```bash
export ALLOWED_HOSTS=awx.example.com,localhost
export CSRF_TRUSTED_ORIGINS=https://awx.example.com
export AWX_HTTPS_BIND_PORT=443
```

---

## Docker Compose Profiles

Use `--profile` flag to enable profiles:

```bash
docker compose --profile hub --profile eda up -d
```

| Profile      | Services             | Use Case                      |
| ------------ | -------------------- | ----------------------------- |
| `` (default) | awx, postgres, redis | Core automation platform      |
| `hub`        | galaxy-ng, pulp      | Enterprise content management |
| `eda`        | eda-controller       | Event-driven automation       |
| `dev`        | dev-tools            | Development and debugging     |

---

## Development & Testing

| Variable                 | Default        | Description                                     |
| ------------------------ | -------------- | ----------------------------------------------- |
| `DEBUG`                  | `False`        | Enable Django debug mode ( never in production) |
| `DJANGO_SETTINGS_MODULE` | `awx.settings` | Django settings module                          |
| `PYTEST_ARGS`            | `-v`           | pytest command-line arguments                   |
| `MOLECULE_ARGS`          | ``             | molecule test arguments                         |
| `HADOLINT_ARGS`          | ``             | hadolint linter arguments                       |

---

## Volume Mounts & Persistence

### Default Volumes

```yaml
volumes:
  awx-data:                  # AWX settings, SSH keys, upload cache
  postgres-data:             # PostgreSQL database files
  redis-data:                # Redis persistence
  receptor-data:             # Receptor socket
  awx-logs:                  # AWX application logs
  awx-projects:              # Project playbooks
```

### Custom Volume Locations

Modify `docker-compose.yml`:

```yaml
volumes:
  awx-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs.example.com,vers=4,soft,timeo=180,bg,tcp,rw
      device: ":/export/awx-data"
```

---

## Configuration File Examples

### .env.production

```bash
# Security
AWX_SECRET_KEY=$(openssl rand -hex 32)
AWX_ADMIN_USER=admin
AWX_ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Database
DATABASE_HOST=postgres
DATABASE_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# Email
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=awx@example.com
EMAIL_HOST_PASSWORD=your-app-password

# Allowed hosts
ALLOWED_HOSTS=awx.example.com
CSRF_TRUSTED_ORIGINS=https://awx.example.com

# Logging
LOG_LEVEL=INFO

# Features
INSIGHTS_TRACKING_STATE=False
DEBUG=False
```

### .env.development

```bash
AWX_ADMIN_PASSWORD=awxadmin
DATABASE_PASSWORD=awxdb
DEBUG=True
LOG_LEVEL=DEBUG
INSIGHTS_TRACKING_STATE=False
```

---

## Using Environment Variables in docker-compose

### As service variables

```yaml
services:
  awx-web:
    environment:
      AWX_ADMIN_USER: ${AWX_ADMIN_USER:-admin}
      AWX_ADMIN_PASSWORD: ${AWX_ADMIN_PASSWORD:-awxadmin}
      SECRET_KEY: ${AWX_SECRET_KEY:-awxsecret}
```

### Loading from file

```bash
docker compose --env-file .env.production up -d
```

### Override at runtime

```bash
export AWX_ADMIN_PASSWORD="my-password"  # pragma: allowlist secret
docker compose up -d
```

---

## Troubleshooting: Environment Variables Not Working

### Issue: Variables not applied

**Solution:** Ensure they're loaded before starting:

```bash
export VAR_NAME=value
docker compose up -d

# Or use env file
docker compose --env-file .env up -d

# Verify set variables
docker compose exec awx-web env | grep AWX_
```

### Issue: Secrets exposed in logs

**Solution:** Use Docker secrets or .env file with restricted permissions:

```bash
chmod 600 .env
docker compose config | grep -i password  # Should not show actual values
```

### Issue: Variables not persisting after restart

**Solution:** Set in .env file, not just terminal:

```bash
echo "AWX_ADMIN_PASSWORD=my-password" >> .env
docker compose up -d
```

---

## Quick Reference: Generate Secure Secrets

```bash
#!/bin/bash
# Generate a .env file with random secrets

cat > .env << EOF
AWX_SECRET_KEY=$(openssl rand -hex 32)
AWX_ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DATABASE_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
GALAXY_ADMIN_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
EOF

chmod 600 .env
```

---

## Performance Tuning

### High-throughput environment

```bash
export CELERY_WORKER_PREFETCH_MULTIPLIER=8
export CELERY_WORKER_MAX_TASKS_PER_CHILD=500
export CALLBACK_QUEUE_CAPACITY=5000
export LOG_AGGREGATOR_LOGGERS=awx
```

### Resource-constrained environment

```bash
export CELERY_WORKER_PREFETCH_MULTIPLIER=1
export CELERY_WORKER_MAX_TASKS_PER_CHILD=200
export LOG_LEVEL=WARNING
export CALLBACK_QUEUE_CAPACITY=100
```

---

## See Also

- [AWX Configuration Guide](https://docs.ansible.com/ansible-tower/latest/html/administration/configure_tower.html)
- [Docker Compose .env Documentation](https://docs.docker.com/compose/compose-file/env-file/)
- [LDAP Configuration Reference](https://docs.ansible.com/ansible-tower/latest/html/administration/ldap_auth.html)
- [OAuth2 Setup Guide](https://docs.ansible.com/ansible-tower/latest/html/administration/social_auth.html)
