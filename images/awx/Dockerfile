# syntax=docker/dockerfile:1
FROM node:18-bookworm AS node-builder

FROM python:3.12-slim AS builder

COPY --from=node-builder /usr/local/ /usr/local/

# Build arguments
ARG AWX_VERSION=devel
ARG AWX_DAB_REF
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
  make \
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
  && rm -rf /var/lib/apt/lists/*

# Clone AWX at specific version
RUN git clone --depth 1 --branch ${AWX_VERSION} https://github.com/ansible/awx.git /awx

# Keep the AWX 24.6.1 DAB dependency aligned with its Django 4.2 lock.
# hadolint ignore=DL3059
RUN python3 - "$AWX_VERSION" "$AWX_DAB_REF" <<'PY'
from pathlib import Path
import sys

awx_version, dab_ref = sys.argv[1:]
if not dab_ref and awx_version == "24.6.1":
  dab_ref = "2024.6.26"
if not dab_ref:
  raise SystemExit(0)

requirements_file = Path("/awx/requirements/requirements_git.txt")
lines = requirements_file.read_text().splitlines()
prefix = "django-ansible-base @ git+https://github.com/ansible/django-ansible-base@"
matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
if len(matches) != 1:
  raise SystemExit(f"Expected one django-ansible-base dependency, found {len(matches)}")

index = matches[0]
suffix = lines[index].split("#egg=", 1)[1]
lines[index] = f"{prefix}{dab_ref}#egg={suffix}"
requirements_file.write_text("\n".join(lines) + "\n")
PY

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
# hadolint ignore=DL3059
RUN python3 /tmp/patch-saml-import.py

# Build the separately maintained AWX UI from its source repository.
# hadolint ignore=DL3059
RUN UI_GIT_REPO=https://github.com/ansible/ansible-ui.git make -C /awx/awx/ui ui

# Final stage
FROM python:3.12-slim

# Build arguments
ARG AWX_VERSION=devel
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
  CMD ["curl", "-f", "http://localhost:8052/api/v2/ping/"]

# Switch to non-root user
# hadolint ignore=DL3066
USER awx

# Default to web entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-web.sh"]
