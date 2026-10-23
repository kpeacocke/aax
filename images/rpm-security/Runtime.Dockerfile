ARG BASE_IMAGE=awx:os-patched
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
COPY install.sh /tmp/aax-install-rpms.sh
RUN --mount=type=bind,source=rpms,target=/tmp/aax-rpms \
    bash /tmp/aax-install-rpms.sh /tmp/aax-rpms && rm /tmp/aax-install-rpms.sh
ARG RUNTIME_USER=root
USER ${RUNTIME_USER}
