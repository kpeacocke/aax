# syntax=docker/dockerfile:1

# Galaxy NG - Ansible content server and Private Automation Hub UI
# Built from upstream galaxy_ng
# Multi-stage build: separates build dependencies from runtime

ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG GALAXY_NG_VERSION=4.9.2

# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

ARG GALAXY_NG_VERSION

# Install build dependencies only
# hadolint ignore=DL3008
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gcc \
  g++ \
  git \
  libpq-dev \
  libldap2-dev \
  libsasl2-dev \
  && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip==24.0 setuptools==69.1.1 wheel==0.42.0 && \
  pip install --no-cache-dir \
  galaxy-ng==${GALAXY_NG_VERSION} \
  gunicorn==22.0.0 \
  psycopg2-binary==2.9.9 \
  django-environ==0.11.2

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF

# Install runtime dependencies only
# hadolint ignore=DL3008
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  curl \
  git \
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
  chown -R galaxy:galaxy /app /var/lib/pulp /etc/pulp

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Patch Galaxy NG settings to fix LOGGING version issue
# hadolint ignore=DL3059
RUN echo "Skipping in-place rewrite of galaxy_ng settings to avoid corruption of INSTALLED_APPS."

# Patch ruamel.yaml metadata to remove clib dependency (same as in Pulp)
# hadolint ignore=DL3059
RUN find /opt/venv/lib/python3.11/site-packages/ruamel.yaml-*.dist-info -name METADATA -exec \
  sed -i 's/Requires-Dist: ruamel\.yaml\.clib.*//' {} \;

# Copy entrypoint script
COPY --chown=galaxy:galaxy entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chown=galaxy:galaxy settings.py /etc/pulp/settings.py
COPY --chown=galaxy:galaxy aax_wsgi.py /app/aax_wsgi.py
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
