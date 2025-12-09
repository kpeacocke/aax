FROM python:3.14-slim

ENV PIP_NO_CACHE_DIR=1 \
  ANSIBLE_NOCOWS=1 \
  PYTHONUNBUFFERED=1

COPY requirements.txt /tmp/requirements.txt

RUN useradd -m -u 1000 -s /bin/bash ansible && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
  openssh-client=1:9.* \
  git=1:2.* \
  ca-certificates=* \
  curl=* \
  less=* \
  vim-tiny=* \
  && rm -rf /var/lib/apt/lists/* && \
  pip install --no-cache-dir -r /tmp/requirements.txt && \
  rm /tmp/requirements.txt

USER ansible
WORKDIR /home/ansible

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import ansible; import ansible_runner; print('healthy')" || exit 1

CMD ["tail", "-f", "/dev/null"]
