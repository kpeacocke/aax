ARG BASE_IMAGE
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
ARG PYTHON
COPY patch_runner_events.py test_runner_events.py /tmp/
RUN "${PYTHON}" /tmp/patch_runner_events.py && \
    "${PYTHON}" /tmp/test_runner_events.py && \
    rm /tmp/patch_runner_events.py /tmp/test_runner_events.py
# hadolint ignore=DL3066
USER 1000
