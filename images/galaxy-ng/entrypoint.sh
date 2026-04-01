#!/bin/bash
set -e

# Default command matches Dockerfile CMD; allow explicit command overrides.
if [ "$#" -eq 0 ]; then
  set -- galaxy-ng
fi
if [ "$1" != "galaxy-ng" ]; then
  exec "$@"
fi

# Wait for PostgreSQL
until PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c '\q' 2>/dev/null; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

echo "PostgreSQL is ready"

# Wait for Redis
until redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping 2>/dev/null | grep -q PONG; do
  echo "Waiting for Redis..."
  sleep 2
done

echo "Redis is ready"

# Wait for Pulp API (use a dedicated URL var to avoid Django settings collisions)
PULP_STATUS_URL="${HUB_PULP_API_URL:-http://pulp-api:24817}"
until python3 -c "
import urllib.request, sys
try:
    urllib.request.urlopen('${PULP_STATUS_URL}/pulp/api/v3/status/', timeout=5)
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  echo "Waiting for Pulp API..."
  sleep 5
done

echo "Pulp API is ready"

# Generate encryption keys if they don't exist
mkdir -p /etc/pulp/certs
if [ ! -f /etc/pulp/certs/database_fields.symmetric.key ]; then
  echo "Generating database encryption key..."
  python -c "from cryptography.fernet import Fernet; key = Fernet.generate_key(); open('/etc/pulp/certs/database_fields.symmetric.key', 'wb').write(key)"
  chmod 644 /etc/pulp/certs/database_fields.symmetric.key
fi

# Use pulpcore settings with a static settings file, which loads plugin apps
# (including galaxy-ng) correctly in this packaging layout.
export PULP_SETTINGS="${PULP_SETTINGS:-/etc/pulp/settings.py}"
export DJANGO_SETTINGS_MODULE='pulpcore.app.settings'

# Skip migrations - database already initialized by Pulp
echo "Skipping migrations (database already initialized)"

# Skip collectstatic - can be done later if needed
echo "Skipping collectstatic"

# Skip admin user creation - can be done later if needed
echo "Skipping admin user creation"

# Start Galaxy NG server
echo "Starting Galaxy NG server..."
exec gunicorn aax_wsgi:application \
  --bind '0.0.0.0:8000' \
  --workers 4 \
  --timeout 90 \
  --access-logfile - \
  --error-logfile -
