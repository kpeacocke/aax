# syntax=docker/dockerfile:1
FROM python:3.11-slim as builder

# Build arguments
ARG AWX_VERSION=24.6.1
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Set working directory
WORKDIR /tmp

# pip runs as root during Docker builds by design; suppress noisy warning.
ENV PIP_ROOT_USER_ACTION=ignore

# Install build dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  git \
  gcc \
  pkg-config \
  python3-dev \
  libpq-dev \
  libffi-dev \
  libssl-dev \
  libldap2-dev \
  libsasl2-dev \
  libxml2-dev \
  libxmlsec1-dev \
  libxmlsec1-openssl \
  libxslt1-dev \
  curl \
  xmlsec1 \
  nodejs \
  npm \
  && rm -rf /var/lib/apt/lists/*

# Clone AWX at specific version
RUN git clone --depth 1 --branch ${AWX_VERSION} https://github.com/ansible/awx.git /awx

# Keep Django in sync with django-ansible-base dependency constraints
RUN sed -i 's/^Django==4.2.10/Django==4.2.26/' /awx/requirements/requirements.txt && \
  sed -i 's/^django==4.2.10/django==4.2.26/' /awx/requirements/requirements.txt && \
  sed -i 's/^sqlparse==0.4.4/sqlparse==0.5.2/' /awx/requirements/requirements.txt && \
  sed -i '/^xmlsec==/d' /awx/requirements/requirements.txt

# Install Python dependencies
WORKDIR /awx
RUN python3 -m pip install --no-cache-dir --prefix=/install \
  -r requirements/requirements.txt \
  -r requirements/requirements_git.txt \
  drf-yasg==1.21.10 \
  gunicorn==22.0.0 \
  psycopg2-binary==2.9.9

# Patch awx/sso/backends.py: wrap the module-level SAML import with try/except
# so that an xmlsec/lxml libxml2 version mismatch doesn't crash every request
# that touches authentication backends.  The stub BaseSAMLAuth keeps
# load_backends() happy; SAMLAuth.authenticate() already returns None when
# SAML credentials are unconfigured, so no SAML functionality is lost.
COPY patch-saml-import.py /tmp/patch-saml-import.py
RUN python3 /tmp/patch-saml-import.py

# Build and stage frontend assets so Django serves compiled UI instead of raw templates.
RUN mkdir -p /awx/awx/ui/build/static /awx/awx/ui_next/build/awx && \
  npm --prefix /awx/awx/ui --loglevel warn ci --legacy-peer-deps && \
  npm --prefix /awx/awx/ui --loglevel warn run compile-strings && \
  NODE_OPTIONS=--max-old-space-size=4096 npm --prefix /awx/awx/ui --loglevel warn run build && \
  cp /awx/awx/ui_next/placeholder_index_awx.html /awx/awx/ui_next/build/awx/index_awx.html

# Final stage
FROM python:3.11-slim

# Build arguments
ARG AWX_VERSION=24.6.1
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Labels
LABEL org.opencontainers.image.title="AAX AWX Controller" \
  org.opencontainers.image.description="AWX Automation Controller built from source for AAX" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
  org.opencontainers.image.url="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.vendor="kpeacocke" \
  org.opencontainers.image.licenses="Apache-2.0"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
  DJANGO_SETTINGS_MODULE=awx.settings.production \
  AWX_LOGGING_MODE=stdout

# Install runtime dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  libpq5 \
  postgresql-client \
  xmlsec1 \
  git \
  curl \
  rsync \
  openssh-client \
  sshpass \
  && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy AWX application
COPY --from=builder /awx /var/lib/awx

# Create AWX user and directories
RUN useradd -m -u 1000 -s /bin/bash awx && \
  mkdir -p /var/lib/awx/projects \
  /var/lib/awx/rsyslog \
  /var/lib/awx/receptor \
  /etc/tower && \
  chown -R awx:awx /var/lib/awx /etc/tower

# Create entrypoint scripts
COPY entrypoint-web.sh /usr/local/bin/entrypoint-web.sh
COPY entrypoint-task.sh /usr/local/bin/entrypoint-task.sh
RUN chmod +x /usr/local/bin/entrypoint-web.sh /usr/local/bin/entrypoint-task.sh

# Switch to AWX directory
WORKDIR /var/lib/awx

# Expose AWX port
EXPOSE 8052

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8052/api/v2/ping/ || exit 1

# Switch to non-root user
USER awx

# Default to web entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-web.sh"]
