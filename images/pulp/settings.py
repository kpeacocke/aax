"""
Pulp Settings for AAX Private Automation Hub
"""
import os
from pathlib import Path

# Build paths
BASE_DIR = Path('/var/lib/pulp')
MEDIA_ROOT = BASE_DIR / 'media'
STATIC_ROOT = BASE_DIR / 'assets'
FILE_UPLOAD_TEMP_DIR = BASE_DIR / 'tmp'

# Ensure directories exist
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
FILE_UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)

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

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'hub-redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

CACHE_ENABLED = True
REDIS_DB = 0
REDIS_CONNECTION_POOL_KWARGS = {'max_connections': 50}

# Celery configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Content settings
CONTENT_ORIGIN = os.getenv('PULP_CONTENT_ORIGIN', 'http://localhost:24816')
ANSIBLE_API_HOSTNAME = os.getenv('PULP_ANSIBLE_API_HOSTNAME', 'http://localhost:5001')
ANSIBLE_CONTENT_HOSTNAME = CONTENT_ORIGIN + '/pulp/content'

# API settings
API_ROOT = '/pulp/'

# Database field encryption
# Generate or use a persistent encryption key
DB_ENCRYPTION_KEY = os.getenv('DB_ENCRYPTION_KEY', '/var/lib/pulp/db-encryption.key')

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'not-a-secure-secret-key-change-this')
ALLOWED_HOSTS = ['*']
DEBUG = False
CONTENT_PATH_PREFIX = '/pulp/content/'

# Security settings
SECRET_KEY = os.getenv('GALAXY_SECRET_KEY', 'change-me-to-a-long-random-string')
ALLOWED_HOSTS = ['*']  # Restrict in production
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5001",
    "http://galaxy-ng:8000",
]
CORS_ALLOW_ALL_ORIGINS = True  # Restrict in production

# Storage backend
DEFAULT_FILE_STORAGE = 'pulpcore.app.models.storage.FileSystem'

# Worker settings
WORKER_TTL = 300

# Task settings
TASK_SERIALIZER = 'json'
RESULT_SERIALIZER = 'json'
ACCEPT_CONTENT = ['json']
TIMEZONE = 'UTC'
ENABLE_UTC = True

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
        'pulpcore': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
            'propagate': False,
        },
        'pulp_ansible': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
            'propagate': False,
        },
        'pulp_container': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
            'propagate': False,
        },
    },
}

# Ansible plugin specific settings
ANSIBLE_DEFAULT_DISTRIBUTION_PATH = 'published'

# Container plugin settings
TOKEN_AUTH_DISABLED = False
PUBLIC_KEY_PATH = '/etc/pulp/pulp-public.pem'
PRIVATE_KEY_PATH = '/etc/pulp/pulp-private.pem'
TOKEN_SIGNATURE_ALGORITHM = 'ES256'
TOKEN_EXPIRATION_TIME = 300

# Content app settings
CONTENT_APP_TTL = 600
