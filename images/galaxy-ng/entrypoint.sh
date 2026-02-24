#!/bin/bash
set -e

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
until curl -f "${PULP_API_ROOT}/api/v3/status/" 2>/dev/null; do
  echo "Waiting for Pulp API..."
  sleep 5
done

echo "Pulp API is ready"

# Generate Django settings
cat > /tmp/galaxy_settings.py << EOF
# Galaxy NG Settings
import os
from pathlib import Path

# Import Pulp settings
from pulpcore.app.settings import *

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
ANSIBLE_API_HOSTNAME = os.getenv('PULP_ANSIBLE_API_HOSTNAME', 'http://localhost:5001')
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

# Installed apps - add Galaxy NG
INSTALLED_APPS += [
    'galaxy_ng',
]

# API settings
API_ROOT = '/api/galaxy/'
GALAXY_API_ROOT = '/api/galaxy/'

# Logging
LOGGING_LEVEL = os.getenv('PULP_LOGGING_LEVEL', 'INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOGGING_LEVEL,
    },
    'loggers': {
        'galaxy_ng': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
            'propagate': False,
        },
    },
}
EOF

export DJANGO_SETTINGS_MODULE=galaxy_ng.app.settings
export PULP_SETTINGS=/tmp/galaxy_settings.py

# Run migrations
echo "Running Galaxy NG migrations..."
django-admin migrate --no-input

# Collect static files
echo "Collecting static files..."
django-admin collectstatic --no-input --clear

# Create admin user if it doesn't exist
echo "Creating admin user..."
django-admin shell << PYEOF
from django.contrib.auth import get_user_model
User = get_user_model()
username = '${GALAXY_ADMIN_USERNAME:-admin}'
password = '${GALAXY_ADMIN_PASSWORD:-changeme}'
email = '${GALAXY_ADMIN_EMAIL:-admin@example.com}'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created admin user: {username}")
else:
    print(f"Admin user already exists: {username}")
PYEOF

# Start Galaxy NG server
echo "Starting Galaxy NG server..."
exec gunicorn galaxy_ng.app.wsgi:application \
  --bind '0.0.0.0:8000' \
  --workers 4 \
  --timeout 90 \
  --access-logfile - \
  --error-logfile -
