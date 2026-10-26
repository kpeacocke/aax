ARG BASE_IMAGE=awx:devel
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
COPY update-os.sh /tmp/aax-update-os.sh
RUN sh /tmp/aax-update-os.sh && rm /tmp/aax-update-os.sh
ARG RUNTIME_USER=root
USER ${RUNTIME_USER}
