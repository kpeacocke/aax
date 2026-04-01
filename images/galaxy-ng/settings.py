"""Galaxy NG/Pulp settings for AAX Hub service."""
import os
from pathlib import Path

BASE_DIR = Path("/var/lib/pulp")
MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = Path("/app/static")
FILE_UPLOAD_TEMP_DIR = BASE_DIR / "tmp"

MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
FILE_UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "hub"),
        "USER": os.getenv("POSTGRES_USER", "galaxy"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "hubpassword"),
        "HOST": os.getenv("POSTGRES_HOST", "hub-postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
    }
}

REDIS_HOST = os.getenv("REDIS_HOST", "hub-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

CACHE_ENABLED = True
REDIS_DB = 0
REDIS_CONNECTION_POOL_KWARGS = {"max_connections": 50}
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

CONTENT_ORIGIN = os.getenv("PULP_CONTENT_ORIGIN", "http://pulp-content:24816")
ANSIBLE_API_HOSTNAME = os.getenv("PULP_ANSIBLE_API_HOSTNAME", "http://galaxy-ng:8000")
ANSIBLE_CONTENT_HOSTNAME = CONTENT_ORIGIN + "/pulp/content"
API_ROOT = "/pulp/"
CONTENT_PATH_PREFIX = "/pulp/content/"

DB_ENCRYPTION_KEY = os.getenv(
    "DB_ENCRYPTION_KEY", "/etc/pulp/certs/database_fields.symmetric.key"
)
SECRET_KEY = os.getenv("GALAXY_SECRET_KEY", os.getenv("SECRET_KEY", "change-me"))

_default_allowed_hosts = ["localhost", "127.0.0.1", "[::1]", "galaxy-ng", "gateway"]
_allowed_hosts_env = os.getenv("GALAXY_ALLOWED_HOSTS", os.getenv("ALLOWED_HOSTS", "")).strip()
if _allowed_hosts_env:
    _parsed = [host.strip() for host in _allowed_hosts_env.split(",") if host.strip()]
    ALLOWED_HOSTS = _parsed or _default_allowed_hosts
else:
    ALLOWED_HOSTS = _default_allowed_hosts

DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
_cors_allow_all_origins = (
    os.getenv("GALAXY_CORS_ALLOW_ALL_ORIGINS", "false").lower() == "true"
)
CORS_ALLOW_ALL_ORIGINS = _cors_allow_all_origins

# Always define CORS_ALLOWED_ORIGINS list (used by Django REST framework even when CORS_ALLOW_ALL_ORIGINS=True)
_cors_allowed_origins_env = os.getenv(
    "GALAXY_CORS_ALLOWED_ORIGINS",
    "http://localhost:15001,http://127.0.0.1:15001",
)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _cors_allowed_origins_env.split(",")
    if origin.strip()
]

DEFAULT_FILE_STORAGE = "pulpcore.app.models.storage.FileSystem"
WORKER_TTL = 300
TASK_SERIALIZER = "json"
RESULT_SERIALIZER = "json"
ACCEPT_CONTENT = ["json"]
TIMEZONE = "UTC"
ENABLE_UTC = True

LOGGING_LEVEL = os.getenv("PULP_LOGGING_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOGGING_LEVEL,
    },
}
