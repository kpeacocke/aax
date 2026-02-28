# syntax=docker/dockerfile:1

# Development Tools for Ansible
# Includes ansible-navigator, ansible-lint, and development utilities
# Multi-stage build: separates build dependencies from runtime

ARG BASE_IMAGE=aax/ee-base:latest

# Stage 1: Builder
# hadolint ignore=DL3007
FROM ${BASE_IMAGE}:latest AS builder

# Build arguments for metadata
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Environment variables
ENV PIP_NO_CACHE_DIR=1 \
  ANSIBLE_NOCOWS=1 \
  PYTHONUNBUFFERED=1 \
  DEBIAN_FRONTEND=noninteractive \
  PIP_ROOT_USER_ACTION=ignore

# Switch to root for installation
# hadolint ignore=DL3002
USER root

# Copy Python requirements
COPY --chown=ansible:ansible requirements.txt /tmp/requirements.txt

# Install build dependencies and Python packages
# hadolint ignore=DL3008
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gcc \
  g++ \
  make \
  libc6-dev \
  libonig-dev && \
  pip install --no-cache-dir -r /tmp/requirements.txt && \
  ansible-navigator --version && \
  ansible-lint --version && \
  rm -rf /var/lib/apt/lists/* && \
  rm -f /tmp/requirements.txt && \
  mkdir -p /home/ansible/.ansible && \
  chown -R ansible:ansible /home/ansible/.ansible

# Stage 2: Runtime
# hadolint ignore=DL3007
FROM ${BASE_IMAGE}:latest

# Build arguments for metadata
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Environment variables
ENV PIP_NO_CACHE_DIR=1 \
  ANSIBLE_NOCOWS=1 \
  PYTHONUNBUFFERED=1 \
  DEBIAN_FRONTEND=noninteractive \
  PAGER=""

# Switch to root for cleanup
USER root

# Copy installed Python packages from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /home/ansible/.ansible /home/ansible/.ansible

# Clean up build artifacts
RUN apt-get update && \
  apt-get purge -y gcc g++ make libc6-dev libonig-dev && \
  apt-get autoremove -y && \
  rm -rf /var/lib/apt/lists/* && \
  chown -R ansible:ansible /home/ansible/.ansible

# OCI metadata labels
LABEL org.opencontainers.image.title="AAX Development Tools" \
  org.opencontainers.image.description="Ansible development tools including ansible-navigator, ansible-lint, and ansible-dev-tools" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
  org.opencontainers.image.url="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.vendor="kpeacocke" \
  org.opencontainers.image.licenses="Apache-2.0"

# Health check to verify ansible-navigator is functional
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD ansible-navigator --version || exit 1

# Switch to non-root user
USER ansible
WORKDIR /workspace

CMD ["bash"]
