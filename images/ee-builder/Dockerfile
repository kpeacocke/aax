# images/ee-builder/Dockerfile
ARG BASE_IMAGE=aax/ee-base:latest
# hadolint ignore=DL3006,DL3007
FROM ${BASE_IMAGE}

USER root

# Build arguments for metadata
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Install ansible-builder
RUN pip install --no-cache-dir \
  "ansible-builder==3.*"

# OCI metadata labels
LABEL org.opencontainers.image.title="AAX Execution Environment Builder" \
  org.opencontainers.image.description="Ansible Execution Environment with ansible-builder for building custom EE images" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
  org.opencontainers.image.url="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.vendor="kpeacocke" \
  org.opencontainers.image.licenses="Apache-2.0"

USER ansible
WORKDIR /workspace

CMD ["bash"]
