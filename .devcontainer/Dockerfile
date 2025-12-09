# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

LABEL maintainer="kpeacocke@gmail.com" \
  description="AAX Development Container with Docker, linting, and validation tools" \
  version="1.1"

# Set shell with pipefail for safer RUN commands
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Define versions as build arguments for easy updates
ARG HADOLINT_VERSION=2.12.0
ARG HADOLINT_SHA256=56de6d5e5ec427e17b74fa48d51271c7fc0d61244bf5c90e828aab8362d55010
ARG MARKDOWNLINT_VERSION=0.39.0
ARG YAMLLINT_VERSION=1.35.1
ARG PRECOMMIT_VERSION=3.6.2
ARG COMMITIZEN_VERSION=3.18.0

# Install base system dependencies (changes infrequently - good for caching)
# hadolint ignore=DL3008
RUN apt-get update \
  && export DEBIAN_FRONTEND=noninteractive \
  && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Docker CLI and Docker Compose (separate layer for better caching)
# hadolint ignore=DL3008
RUN install -m 0755 -d /etc/apt/keyrings \
  && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
  && chmod a+r /etc/apt/keyrings/docker.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
  docker-ce-cli \
  docker-compose-plugin \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install development tools (separate layer - changes occasionally)
# hadolint ignore=DL3008
RUN apt-get update \
  && export DEBIAN_FRONTEND=noninteractive \
  && apt-get install -y --no-install-recommends \
  build-essential \
  git \
  jq \
  make \
  python3 \
  python3-pip \
  python3-venv \
  shellcheck \
  vim \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install Node.js LTS and markdownlint (separate layer for clarity)
# hadolint ignore=DL3008,DL3016
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && npm install -g "markdownlint-cli@${MARKDOWNLINT_VERSION}" \
  && npm cache clean --force

# Switch to non-root user for security
USER vscode
WORKDIR /workspace

# Install hadolint with checksum verification
RUN mkdir -p /home/vscode/.local/bin \
  && curl -sL -o /home/vscode/.local/bin/hadolint \
  "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-x86_64" \
  && echo "${HADOLINT_SHA256}  /home/vscode/.local/bin/hadolint" | sha256sum -c - \
  && chmod +x /home/vscode/.local/bin/hadolint

# Install Python-based tools in user space
# Ubuntu 24.04 has Python 3.12+ with pip that supports --break-system-packages
RUN pip3 install --user --no-cache-dir --break-system-packages \
  "yamllint==${YAMLLINT_VERSION}" \
  "pre-commit==${PRECOMMIT_VERSION}" \
  "commitizen==${COMMITIZEN_VERSION}"

# Update PATH for user-installed tools
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Create verification script for runtime health checks instead of build-time failures
RUN printf '#!/bin/bash\nset -e\necho "Verifying tool installations..."\n' > /home/vscode/.local/bin/verify-tools \
  && printf 'docker --version\ndocker compose version\nhadolint --version\nshellcheck --version\n' >> /home/vscode/.local/bin/verify-tools \
  && printf 'yamllint --version\nmarkdownlint --version\npre-commit --version\ncz version\n' >> /home/vscode/.local/bin/verify-tools \
  && printf 'echo "All tools verified successfully!"\n' >> /home/vscode/.local/bin/verify-tools \
  && chmod +x /home/vscode/.local/bin/verify-tools

# Set default command to bash (typical for devcontainer)
CMD ["/bin/bash"]
