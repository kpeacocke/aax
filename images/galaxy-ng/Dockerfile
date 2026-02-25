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
    nodejs \
    npm && \
    rm -rf /var/lib/apt/lists/*

# Create galaxy user and directories
RUN groupadd -g 1000 galaxy && \
    useradd -u 1000 -g galaxy -m -d /app -s /bin/bash galaxy && \
    mkdir -p /app/static && \
    mkdir -p /var/lib/pulp/{media,assets,tmp} && \
    chown -R galaxy:galaxy /app /var/lib/pulp

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    galaxy-ng==${GALAXY_NG_VERSION} \
    gunicorn==22.0.0 \
    psycopg2-binary==2.9.9 \
    django-environ==0.11.2

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
