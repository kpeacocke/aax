FROM python:3.14.10-slim AS runtime-base

FROM python:3.15-slim-bookworm AS pip-builder
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && \
  rm -rf /var/lib/apt/lists/*
COPY pip-security /patches
WORKDIR /source
RUN sh /patches/build.sh

FROM runtime-base AS runtime-security-builder
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev libbluetooth-dev git curl xz-utils && rm -rf /var/lib/apt/lists/*
COPY python-security /patches
RUN sh /patches/build.sh

FROM runtime-base AS openssh-security-builder
# hadolint ignore=DL3008
RUN sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    openssh-client dpkg-dev devscripts quilt patchutils python3-paramiko && apt-get build-dep -y openssh
COPY openssh-security/client-lifetime.patch openssh-security/build.sh /patches/
WORKDIR /source
RUN sh /patches/build.sh
COPY openssh-security/test_rekey.py openssh-security/verify.sh /patches/
RUN sh /patches/verify.sh

FROM runtime-base

# Build arguments for metadata
ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

# Environment variables
ENV PIP_NO_CACHE_DIR=1 \
  ANSIBLE_NOCOWS=1 \
  PYTHONUNBUFFERED=1 \
  PIP_CONSTRAINT=/etc/pip/constraints.txt \
  DEBIAN_FRONTEND=noninteractive \
  PIP_ROOT_USER_ACTION=ignore

# Copy configuration and requirements
COPY requirements.txt /tmp/requirements.txt
COPY constraints.txt /etc/pip/constraints.txt
COPY ansible.cfg /etc/ansible/ansible.cfg
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --from=pip-builder /wheels /tmp/aax-pip-wheels
COPY --from=runtime-security-builder /output/ /
COPY python-security/test_runtime.py /tmp/aax-python-security-test.py
COPY --from=openssh-security-builder /output/packages/ /tmp/aax-openssh-packages/
COPY --from=openssh-security-builder /output/provenance/ /usr/local/share/aax/openssh-security/
RUN python /tmp/aax-python-security-test.py && rm /tmp/aax-python-security-test.py

# Install system packages, create user, install Python packages
# hadolint ignore=DL3008,DL3001
RUN mkdir -p /etc/ansible && \
  useradd -m -u 1000 -s /bin/bash ansible && \
  apt-get update && \
  apt-get upgrade -y && \
  apt-get install -y --no-install-recommends \
  openssh-client \
  git \
  ca-certificates \
  curl \
  less \
  vim-tiny \
  sshpass \
  rsync \
  jq && \
  apt-get install -y --no-install-recommends /tmp/aax-openssh-packages/*.deb && \
  test "$(dpkg-query -W -f='${Version}' openssh-client)" = \
    "$(cat /usr/local/share/aax/openssh-security/vendor-version)+aax.1" && \
  ssh -V && \
  rm /tmp/aax-openssh-packages/*.deb && \
  rm -rf /var/lib/apt/lists/* && \
  pip install --no-cache-dir /tmp/aax-pip-wheels/*.whl && \
  pip install --no-cache-dir -r /tmp/requirements.txt && \
  pip check && \
  rm /tmp/requirements.txt /tmp/aax-pip-wheels/*.whl && \
  chmod +x /usr/local/bin/entrypoint.sh

# OCI metadata labels
LABEL org.opencontainers.image.title="AAX Ansible Execution Environment" \
  org.opencontainers.image.description="Base execution environment for Ansible automation" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
  org.opencontainers.image.url="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.vendor="kpeacocke" \
  org.opencontainers.image.licenses="Apache-2.0"

# Health check to verify Ansible installation
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD ["python3", "-c", "import ansible; import ansible_runner"]

# Switch to non-root user
# hadolint ignore=DL3066
USER ansible
WORKDIR /home/ansible

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
