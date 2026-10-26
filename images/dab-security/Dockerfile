FROM python:3.12-slim-bookworm AS builder
ARG DAB_REVISION=ef2ceb250322272451ce220d10c20947898d36d3
ARG DAB_VERSION=2026.10.9.0.dev104+aax.2
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
      git build-essential libldap2-dev libsasl2-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /source
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends libxmlsec1-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*
RUN git init && git remote add origin https://github.com/ansible/django-ansible-base.git && \
    git fetch --depth 1 origin "${DAB_REVISION}" && git checkout --detach FETCH_HEAD
COPY oauth-organization.patch /tmp/oauth-organization.patch
COPY requirements-test.txt /tmp/requirements-test.txt
COPY apply-oauth-patch.py /tmp/apply-oauth-patch.py
RUN python /tmp/apply-oauth-patch.py /tmp/oauth-organization.patch
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_DJANGO_ANSIBLE_BASE=${DAB_VERSION}
# BuildKit retains the download cache outside the resulting image.
# hadolint ignore=DL3042
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install '.[all]' djangorestframework==3.18.2 \
      -r /tmp/requirements-test.txt && python -m pip check
RUN DJANGO_SETTINGS_MODULE=test_app.sqlite3settings OTEL_SDK_DISABLED=true \
      python -m pytest -q -x -o addopts= test_app/tests/oauth2_provider && \
    python -m pip wheel --no-deps --wheel-dir /wheels .
FROM scratch
COPY --from=builder /wheels /wheels
