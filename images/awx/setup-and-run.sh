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
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'awxpass'),
        'HOST': os.getenv('DATABASE_HOST', 'awx-postgres'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
        'ATOMIC_REQUESTS': True,
        'CONN_MAX_AGE': 0,
    }
}

# AWX specific settings
SECRET_KEY = os.getenv('SECRET_KEY', 'awxsecret')
DEBUG = False
ALLOWED_HOSTS = ['*']

# Broadcast websocket setting
BROADCAST_WEBSOCKET_SECRET = os.getenv('SECRET_KEY', 'awxsecret')
SETTINGS_EOF

# Execute the launcher
exec "$@"
