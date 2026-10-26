ARG BASE_IMAGE=awx:python-patched
ARG DAB_IMAGE=aax/dab-security:eda
# hadolint ignore=DL3006
FROM ${DAB_IMAGE} AS dab
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
ARG PYTHON=/var/lib/awx/venv/awx/bin/python
# hadolint ignore=DL3066
USER root
COPY --from=dab /wheels /tmp/aax-dab-wheels
RUN "${PYTHON}" -m pip install --no-cache-dir --upgrade /tmp/aax-dab-wheels/*.whl \
      djangorestframework==3.18.2 && \
    "${PYTHON}" -m pip check && \
    "${PYTHON}" -c 'import autobahn.twisted.websocket' && rm /tmp/aax-dab-wheels/*.whl
# hadolint ignore=DL3066
USER 1000
