FROM python:3.14-slim

ARG VERSION=dev
ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.title="Ansible Execution Environment" \
  org.opencontainers.image.description="Base execution environment for Ansible automation" \
  org.opencontainers.image.version="${VERSION}" \
  org.opencontainers.image.created="${BUILD_DATE}" \
  org.opencontainers.image.revision="${VCS_REF}" \
  org.opencontainers.image.authors="kpeacocke <krpeacocke@gmail.com>" \
  org.opencontainers.image.source="https://github.com/kpeacocke/AAX" \
  org.opencontainers.image.url="https://github.com/kpeacocke/AAX"

ENV PIP_NO_CACHE_DIR=1 \
  ANSIBLE_NOCOWS=1 \
  PYTHONUNBUFFERED=1

COPY requirements.txt /tmp/requirements.txt
COPY ansible.cfg /etc/ansible/ansible.cfg

# hadolint ignore=DL3008
RUN mkdir -p /etc/ansible && \
  useradd -m -u 1000 -s /bin/bash ansible && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
  openssh-client \
  git \
  ca-certificates \
  curl \
  less \
  vim-tiny \
  sshpass \
  rsync \
  jq \
  && rm -rf /var/lib/apt/lists/* && \
  pip install --no-cache-dir -r /tmp/requirements.txt && \
  rm /tmp/requirements.txt

USER ansible
WORKDIR /home/ansible

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import ansible; import ansible_runner" || exit 1

CMD ["tail", "-f", "/dev/null"]
