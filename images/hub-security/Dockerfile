ARG BASE_IMAGE=galaxy-ng:python-patched
ARG DAB_IMAGE=aax/dab-security:hub
# hadolint ignore=DL3006
FROM ${DAB_IMAGE} AS dab
FROM python:3.15-slim-bookworm AS builder
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends patch && \
    rm -rf /var/lib/apt/lists/*
ADD https://files.pythonhosted.org/packages/71/d2/acfd35c9c47c746807eb9e6ab804c1f60cecdfef114bff84e37b9030ee0e/pulpcore-3.105.24.tar.gz /tmp/pulpcore.tar.gz
ADD https://files.pythonhosted.org/packages/21/db/24b4be78d98242004ccb439118d771b72875e360e717537a964e7e29c015/pulp_glue-0.39.5.tar.gz /tmp/pulp-glue.tar.gz
COPY pulpcore.patch pulp-glue.patch /patches/
RUN echo '8005019e9669c39daa477698c69a163a389c2072394dbde8b21ec4b7cd04164c  /tmp/pulpcore.tar.gz' > /tmp/source-checksums && \
    echo '2230cb966170180b0a0ab224d8c79c19099816a494e1ba7acd3c4de08c98a233  /tmp/pulp-glue.tar.gz' >> /tmp/source-checksums && \
    sha256sum --check /tmp/source-checksums && \
    mkdir -p /source/pulpcore /source/pulp-glue && \
    tar -xzf /tmp/pulpcore.tar.gz --strip-components=1 -C /source/pulpcore && \
    tar -xzf /tmp/pulp-glue.tar.gz --strip-components=1 -C /source/pulp-glue && \
    patch -d /source/pulpcore -p1 < /patches/pulpcore.patch && \
    patch -d /source/pulp-glue -p1 < /patches/pulp-glue.patch && \
    python -m pip wheel --no-cache-dir --no-deps --wheel-dir /wheels \
      /source/pulpcore /source/pulp-glue
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
ARG DAB_VERSION
# hadolint ignore=DL3066
USER root
COPY --from=builder /wheels /tmp/aax-wheels
COPY --from=dab /wheels /tmp/aax-wheels
COPY galaxy.patch galaxy-pyproject.patch patch-galaxy.sh /tmp/
COPY test_telemetry.py /tmp/aax-test-hub-telemetry.py
RUN bash /tmp/patch-galaxy.sh /app /tmp "${DAB_VERSION}" && \
    /venv/bin/python -m pip wheel --no-deps --wheel-dir /tmp/aax-wheels /app && \
    /venv/bin/python -m pip install --no-cache-dir --upgrade /tmp/aax-wheels/*.whl \
      aiohttp==3.14.5 social-auth-core==6.2.0 social-auth-app-django==7.2.0 \
      djangorestframework==3.18.2 multidict==6.9.1 oauthlib==4.0.1 tablib==3.10.0 \
      opentelemetry-api==1.45.2 opentelemetry-sdk==1.45.2 opentelemetry-proto==1.45.2 \
      opentelemetry-exporter-otlp-proto-common==1.45.2 \
      opentelemetry-exporter-otlp-proto-http==1.45.2 opentelemetry-semantic-conventions==0.66b2 \
      black==26.10.1 filelock==4.2.1 && \
    /venv/bin/python -m pip check && \
    /venv/bin/python /tmp/aax-test-hub-telemetry.py && \
    rm /tmp/aax-wheels/*.whl /tmp/aax-test-hub-telemetry.py
# hadolint ignore=DL3066
USER galaxy
