# Base image with Docker CLI
FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install system dependencies and shellcheck all in one layer as root
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    software-properties-common \
    build-essential \
    git \
    make \
    vim \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    shellcheck \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI and Docker Compose
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get -y install --no-install-recommends \
    docker-ce-cli \
    docker-compose-plugin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and markdownlint as root
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g markdownlint-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch to vscode user for user-level tools
USER vscode
WORKDIR /home/vscode

# Create .local/bin directory
RUN mkdir -p /home/vscode/.local/bin

# Install hadolint (Dockerfile linter)
RUN wget -qO /home/vscode/.local/bin/hadolint https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64 \
    && chmod +x /home/vscode/.local/bin/hadolint

# Install Python tools (yamllint, pre-commit, commitizen) - use --break-system-packages for container environment
RUN pip3 install --user --no-cache-dir --break-system-packages \
    yamllint \
    pre-commit \
    commitizen

# Add user bin to PATH
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Set working directory
WORKDIR /workspace

# Verify installations (break into separate RUN to isolate any failures)
RUN docker --version
RUN docker compose version
RUN hadolint --version
RUN shellcheck --version
RUN yamllint --version
RUN markdownlint --version
RUN pre-commit --version
RUN cz version
