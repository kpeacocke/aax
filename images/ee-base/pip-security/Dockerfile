FROM python:3.12-slim-bookworm AS builder
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && \
    rm -rf /var/lib/apt/lists/*
COPY pip-security /patches
WORKDIR /source
RUN sh /patches/build.sh
FROM scratch
COPY --from=builder /wheels /wheels
