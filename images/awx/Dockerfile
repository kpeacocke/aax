# syntax=docker/dockerfile:1
FROM python:3.11-slim as builder

# Build arguments
ARG AWX_VERSION=24.6.1
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Set working directory
WORKDIR /tmp

# Install build dependencies
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  git=1:2.43.0-1ubuntu1 \
  gcc=4:13.2.0-1ubuntu1 \
  python3-dev=3.12.1-1ubuntu1 \
  libpq-dev=15.5-1ubuntu1 \
  libffi-dev=3.4.4-2 \
  libssl-dev=3.1.4-1ubuntu3 \
  curl=7.87.0-1ubuntu1 \
  xmlsec1=1.2.37-3 \
  && rm -rf /var/lib/apt/lists/*

# Clone AWX at specific version
RUN git clone --depth 1 --branch ${AWX_VERSION} https://github.com/ansible/awx.git /awx

# Install Python dependencies
WORKDIR /awx
RUN pip install --no-cache-dir --prefix=/install \
  -r requirements/requirements.txt \
  -r requirements/requirements_git.txt

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
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX"

# Environment variables
ENV PYTHONUNBUFFERED=1 \
  DJANGO_SETTINGS_MODULE=awx.settings.production \
  AWX_LOGGING_MODE=stdout

# Install runtime dependencies
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  libpq5=15.5-1ubuntu1 \
  postgresql-client=15.5-1ubuntu1 \
  xmlsec1=1.2.37-3 \
  git=1:2.43.0-1ubuntu1 \
  curl=7.87.0-1ubuntu1 \
  rsync=3.2.7-1ubuntu1 \
  openssh-client=1:9.3p1-1ubuntu1 \
  sshpass=1.10-1 \
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

# Default to web entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-web.sh"]
