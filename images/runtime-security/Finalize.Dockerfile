ARG BASE_IMAGE
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
COPY remove-build-setuptools.sh /tmp/aax-remove-build-setuptools.sh
RUN sh /tmp/aax-remove-build-setuptools.sh && \
    rm /tmp/aax-remove-build-setuptools.sh
ARG RUNTIME_USER=root
USER ${RUNTIME_USER}
