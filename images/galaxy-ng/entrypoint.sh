#!/bin/bash
set -e

# Allow command override for testing
if [ "$#" -gt 0 ]; then
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

# Wait for Pulp API
until curl -f "${PULP_API_ROOT}/pulp/api/v3/status/" 2>/dev/null; do
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

# Unset PULP_* variables that conflict with Galaxy NG's dynaconf validation
# We set CONTENT_ORIGIN instead for Galaxy NG
unset PULP_API_ROOT PULP_ANSIBLE_API_HOSTNAME

# Set environment variables for Galaxy NG configuration
export DJANGO_SETTINGS_MODULE='galaxy_settings'
export PYTHONPATH="/tmp:$PYTHONPATH"

# Generate Galaxy settings module with proper layering: pulpcore → galaxy_ng → our overrides
cat > /tmp/galaxy_settings.py << 'EOF'
# Custom Galaxy NG Settings Module
import os

# Layer 1: Import Pulpcore settings (includes all Django contrib apps)
from pulpcore.app.settings import *

# Layer 2: Import Galaxy NG settings additions
from galaxy_ng.app.settings import MIDDLEWARE, INSTALLED_APPS as GX_APPS, AUTH_USER_MODEL

# Merge Galaxy NG apps into INSTALLED_APPS
INSTALLED_APPS.extend(GX_APPS)

# Layer 3: Our custom overrides
# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'hub'),
        'USER': os.getenv('POSTGRES_USER', 'galaxy'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'hubpassword'),
        'HOST': os.getenv('POSTGRES_HOST', 'hub-postgres'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 0,
    }
}

# Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'hub-redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CACHE_ENABLED = True

# Pulp integration
CONTENT_ORIGIN = os.getenv('PULP_CONTENT_ORIGIN', 'http://localhost:24816')
ANSIBLE_CONTENT_HOSTNAME = CONTENT_ORIGIN + '/pulp/content'

# Galaxy NG specific
GALAXY_REQUIRE_CONTENT_APPROVAL = os.getenv('GALAXY_REQUIRE_CONTENT_APPROVAL', 'true').lower() == 'true'
GALAXY_SIGNATURE_UPLOAD_ENABLED = os.getenv('GALAXY_SIGNATURE_UPLOAD_ENABLED', 'false').lower() == 'true'
GALAXY_AUTO_SIGN_COLLECTIONS = os.getenv('GALAXY_AUTO_SIGN_COLLECTIONS', 'false').lower() == 'true'
GALAXY_COLLECTION_SIGNING_SERVICE = os.getenv('GALAXY_COLLECTION_SIGNING_SERVICE', '')
GALAXY_CONTAINER_SIGNING_SERVICE = os.getenv('GALAXY_CONTAINER_SIGNING_SERVICE', '')

# Security
SECRET_KEY = os.getenv('GALAXY_SECRET_KEY', 'change-me-to-a-long-random-string')
ALLOWED_HOSTS = os.getenv('GALAXY_ALLOWED_HOSTS', '*').split(',')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'

# Static files
STATIC_ROOT = '/app/static'

# Media files
MEDIA_ROOT = '/var/lib/pulp/media'

# API settings - Must be paths only, not full URLs
API_ROOT = '/api/galaxy/'
GALAXY_API_ROOT = '/api/galaxy/'
EOF

# Skip migrations - database already initialized by Pulp
echo "Skipping migrations (database already initialized)"

# Skip collectstatic - can be done later if needed
echo "Skipping collectstatic"

# Skip admin user creation - can be done later if needed
echo "Skipping admin user creation"

# Start Galaxy NG server
echo "Starting Galaxy NG server..."
exec gunicorn pulpcore.app.wsgi:application \
  --bind '0.0.0.0:8000' \
  --workers 4 \
  --timeout 90 \
  --access-logfile - \
  --error-logfile -
