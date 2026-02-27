# syntax=docker/dockerfile:1

# Galaxy NG - Ansible content server and Private Automation Hub UI
# Built from upstream galaxy_ng

ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

FROM python:3.11-slim-bookworm

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF
ARG GALAXY_NG_VERSION=4.9.2

# Install system dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gcc \
  g++ \
  git \
  libpq-dev \
  libldap2-dev \
  libsasl2-dev \
  curl \
  gnupg \
  postgresql-client \
  redis-tools \
  nodejs \
  npm && \
  rm -rf /var/lib/apt/lists/*

# Create galaxy user and directories
RUN groupadd -g 1000 galaxy && \
  useradd -u 1000 -g galaxy -m -d /app -s /bin/bash galaxy && \
  mkdir -p /app/static && \
  mkdir -p /var/lib/pulp/media /var/lib/pulp/assets /var/lib/pulp/tmp && \
  mkdir -p /etc/pulp/certs && \
  chown -R galaxy:galaxy /app /var/lib/pulp

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip==24.0 setuptools==69.1.1 wheel==0.42.0 && \
  pip install --no-cache-dir \
  galaxy-ng==${GALAXY_NG_VERSION} \
  gunicorn==22.0.0 \
  psycopg2-binary==2.9.9 \
  django-environ==0.11.2

# Patch Galaxy NG settings to fix LOGGING version issue
# hadolint ignore=DL3059
RUN python -c "import re; \
  f = open('/usr/local/lib/python3.11/site-packages/galaxy_ng/app/settings.py', 'r'); \
  content = f.read(); f.close(); \
  content = content.replace('LOGGING = {', 'LOGGING = {\\n    \"version\": 1,\\n    \"disable_existing_loggers\": False,\\n    \"formatters\": {\\n        \"simple\": {\\n            \"format\": \"%(asctime)s %(name)-12s %(levelname)-8s %(message)s\",\\n        },\\n    },'); \
  content = content.replace(\"    'dynaconf_merge',\\n\", ''); \
  content = content.replace('    \\\"dynaconf_merge\\\": True,', ''); \
  f = open('/usr/local/lib/python3.11/site-packages/galaxy_ng/app/settings.py', 'w'); \
  f.write(content); f.close()"

# Patch ruamel.yaml metadata to remove clib dependency (same as in Pulp)
# hadolint ignore=DL3059
RUN find /usr/local/lib/python3.11/site-packages/ruamel.yaml-*.dist-info -name METADATA -exec \
  sed -i 's/Requires-Dist: ruamel\.yaml\.clib.*//' {} \;

# Copy entrypoint script
COPY --chown=galaxy:galaxy entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# OCI metadata labels
LABEL org.opencontainers.image.title="AAX Galaxy NG" \
  org.opencontainers.image.description="Galaxy NG - Private Automation Hub for Ansible content" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
  org.opencontainers.image.url="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.vendor="kpeacocke" \
  org.opencontainers.image.licenses="Apache-2.0"

# Set working directory and user
WORKDIR /app
USER galaxy

# Expose port
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["galaxy-ng"]
