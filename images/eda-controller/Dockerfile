# syntax=docker/dockerfile:1

# Event-Driven Ansible Controller
# Provides event-driven automation interface with ansible-rulebook
# Multi-stage build: separates build dependencies from runtime

ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF
ARG EDA_VERSION=1.1.3

# Stage 1: Builder
FROM python:3.11-slim-bookworm AS builder

ARG EDA_VERSION

# Install build dependencies only
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install Python dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip==24.0 setuptools==69.1.1 wheel==0.42.0 && \
    pip install --no-cache-dir \
    ansible-rulebook==${EDA_VERSION} \
    aiohttp==3.9.2 \
    psycopg2-binary==2.9.9 \
    pydantic==2.6.1 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    python-daemon==3.0.1

# Stage 2: Runtime
FROM python:3.11-slim-bookworm

ARG VERSION
ARG BUILD_DATE
ARG VCS_REF

# Install runtime dependencies only (including Java for Drools engine)
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    jq \
    openjdk-17-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Create eda user and home directory
RUN groupadd -g 1001 eda && \
    useradd -u 1001 -g eda -m -d /home/eda -s /bin/bash eda

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create configuration directory
RUN mkdir -p /etc/eda /var/log/eda && \
    chown -R eda:eda /etc/eda /var/log/eda

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set up OCI labels
LABEL org.opencontainers.image.title="AAX Event-Driven Ansible Controller" \
    org.opencontainers.image.description="Event-driven automation with ansible-rulebook" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.revision="${VCS_REF}" \
    org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
    org.opencontainers.image.url="https://github.com/kpeacocke/AAX" \
    org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
    org.opencontainers.image.vendor="kpeacocke" \
    org.opencontainers.image.licenses="Apache-2.0"

# Health check for ansible-rulebook service
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to eda user
USER eda

# Set working directory
WORKDIR /home/eda

# Expose API port
EXPOSE 5000

# Default entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
