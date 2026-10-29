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
COPY patch_awx_dynaconf.py /tmp/aax-patch-awx-dynaconf.py
RUN "${PYTHON}" -m pip install --no-cache-dir --upgrade /tmp/aax-dab-wheels/*.whl \
      djangorestframework==3.18.2 && \
    "${PYTHON}" /tmp/aax-patch-awx-dynaconf.py && \
    "${PYTHON}" -m pip check && \
    "${PYTHON}" -c 'import autobahn.twisted.websocket' && \
    rm /tmp/aax-dab-wheels/*.whl /tmp/aax-patch-awx-dynaconf.py
RUN settings_file="$(mktemp /tmp/aax-production-settings-XXXXXX.py)" && \
    printf 'AAX_TEST = True\n' > "$settings_file" && \
    AWX_MODE=production DJANGO_SETTINGS_MODULE=awx.settings AWX_SETTINGS_FILE="$settings_file" \
      SKIP_SECRET_KEY_CHECK=yes SKIP_PG_VERSION_CHECK=yes AWX_SKIP_CREDENTIAL_TYPES_DISCOVER=yes \
      "${PYTHON}" -c 'from django.conf import settings; assert settings.AAX_TEST' && \
    if AWX_MODE=production DJANGO_SETTINGS_MODULE=awx.settings \
      AWX_SETTINGS_FILE=/tmp/aax-missing-settings.py AWX_SETTINGS_DIR=/tmp/aax-missing-settings-dir \
      SKIP_SECRET_KEY_CHECK=yes SKIP_PG_VERSION_CHECK=yes AWX_SKIP_CREDENTIAL_TYPES_DISCOVER=yes \
      "${PYTHON}" -c 'from django.conf import settings; print(settings.DEBUG)' > /tmp/aax-missing-settings.log 2>&1; \
    then echo 'AWX accepted missing production settings' >&2; exit 1; fi && \
    cat /tmp/aax-missing-settings.log && \
    grep -F 'No AWX configuration found at' /tmp/aax-missing-settings.log && \
    rm /tmp/aax-missing-settings.log && \
    rm "$settings_file"
# hadolint ignore=DL3066
USER 1000
