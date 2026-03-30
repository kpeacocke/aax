#!/bin/bash
set -e

# Create settings directory
mkdir -p /etc/tower

# Generate settings.py from environment variables
cat > /etc/tower/settings.py << 'SETTINGS_EOF'
import os
from pathlib import Path

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME', 'awx'),
        'USER': os.getenv('DATABASE_USER', 'awx'),
        'PASSWORD': os.environ['DATABASE_PASSWORD'],
        'HOST': os.getenv('DATABASE_HOST', 'awx-postgres'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': 0,
    }
}

# AWX specific settings
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = False
_allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]
else:
    # Restrictive defaults for local/controller service names.
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'awx', 'awx-web']

# Broadcast websocket setting
BROADCAST_WEBSOCKET_SECRET = os.environ['SECRET_KEY']
SETTINGS_EOF

# Execute the launcher
exec "$@"
