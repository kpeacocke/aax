ARG BASE_IMAGE=quay.io/centos/centos@sha256:6f8045fc4f552544d8a401d61848bafc8d06ca7c11897c5b54a2c37fc419a20a
FROM ${BASE_IMAGE}

# The nested Podman API runs as root inside its isolated privileged service.
# hadolint ignore=DL3002
USER 0
# hadolint ignore=DL3041
RUN dnf -y upgrade && \
    dnf -y install podman curl-minimal ca-certificates && \
    dnf clean all && \
    rm -rf /var/cache/dnf

RUN mkdir -p /etc/containers /var/lib/containers/storage /run/containers/storage && \
    printf '[storage]\ndriver = "vfs"\ngraphroot = "/var/lib/containers/storage"\nrunroot = "/run/containers/storage"\n' \
      > /etc/containers/storage.conf

VOLUME ["/var/lib/containers/storage"]
EXPOSE 8888
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=5 \
  CMD ["curl", "--fail", "--silent", "http://127.0.0.1:8888/_ping"]
ENTRYPOINT ["podman", "system", "service", "--time=0", "tcp://0.0.0.0:8888"]
