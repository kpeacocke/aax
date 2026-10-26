ARG BASE_IMAGE
ARG PIP_IMAGE=aax/pip-security:devel
# hadolint ignore=DL3006
FROM ${PIP_IMAGE} AS pip-security
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
ARG PYTHON
ARG REQUIREMENTS
COPY ${REQUIREMENTS} /tmp/aax-runtime-requirements.txt
COPY --from=pip-security /wheels /tmp/aax-pip-wheels
RUN "${PYTHON}" -m pip install --no-cache-dir /tmp/aax-pip-wheels/*.whl && \
    "${PYTHON}" -m pip install --no-cache-dir --upgrade -r /tmp/aax-runtime-requirements.txt && \
    "${PYTHON}" -m pip check && \
    rm /tmp/aax-runtime-requirements.txt /tmp/aax-pip-wheels/*.whl
ARG RUNTIME_USER
# hadolint ignore=DL3066
USER ${RUNTIME_USER}
