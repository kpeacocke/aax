ARG BASE_IMAGE=eda-decision-environment:devel
ARG PIP_IMAGE=aax/pip-security:devel
ARG DROOLS_IMAGE=ansible-rulebook:patched
# hadolint ignore=DL3006
FROM ${PIP_IMAGE} AS pip-security
# hadolint ignore=DL3006
FROM ${DROOLS_IMAGE} AS drools
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
RUN dnf -y remove tracker-miners webkit2gtk3-jsc && dnf clean all && \
    rm /app/.local/lib/python3.12/site-packages/drools/jars/*.jar
COPY --from=drools /usr/local/lib/python3.12/site-packages/drools/jars/drools-ansible-rulebook-integration-runtime-2.0.1-SNAPSHOT-HA.jar /app/.local/lib/python3.12/site-packages/drools/jars/
COPY --from=pip-security --chown=1001:0 /wheels /tmp/aax-pip-wheels
COPY --chown=1001:0 requirements-decision-environment.txt /tmp/aax-decision-requirements.txt
# hadolint ignore=DL3066
USER 1001
RUN python3.12 -m pip install --no-cache-dir --user /tmp/aax-pip-wheels/*.whl && \
    python3.12 -m pip install --no-cache-dir --user --upgrade -r /tmp/aax-decision-requirements.txt && \
    python3.12 -m pip check && python3.12 -m pip cache purge && \
    rm /tmp/aax-pip-wheels/*.whl /tmp/aax-decision-requirements.txt
