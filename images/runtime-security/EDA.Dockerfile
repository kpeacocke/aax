ARG BASE_IMAGE=eda-controller:python-patched
ARG DAB_IMAGE=aax/dab-security:eda
# hadolint ignore=DL3006
FROM ${DAB_IMAGE} AS dab
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
COPY eda-source.patch /tmp/eda-source.patch
COPY test_eda_crypto.py /tmp/test_eda_crypto.py
COPY pin_eda_dab.py /tmp/pin_eda_dab.py
COPY --from=dab /wheels /tmp/aax-eda-wheel
RUN git -C /app/src apply /tmp/eda-source.patch && \
    /app/venv/bin/python /tmp/pin_eda_dab.py /app/src/pyproject.toml /tmp/aax-eda-wheel && \
    /app/venv/bin/python -m pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/aax-eda-wheel /app/src && \
    /app/venv/bin/python -m pip install --no-cache-dir --upgrade /tmp/aax-eda-wheel/*.whl \
      cryptography==50.0.2 msal==1.39.0 pyOpenSSL==26.4.0 \
      PyNaCl==1.6.2 Pygments==2.20.0 autobahn==26.10.2 black==26.10.1 \
      djangorestframework==3.18.2 ecdsa==0.19.2 idna==3.18 oauthlib==4.0.0 \
      httpie==3.2.4 pytest==9.0.3 requests==2.34.2 setuptools==84.2.1 && \
    /app/venv/bin/python -m pip check && \
    /app/venv/bin/python -c 'import daphne.server' && \
    /app/venv/bin/python /tmp/test_eda_crypto.py && \
    rm /tmp/eda-source.patch /tmp/test_eda_crypto.py /tmp/pin_eda_dab.py /tmp/aax-eda-wheel/*.whl
RUN PYTHONUSERBASE=/app/.local /usr/bin/python3.12 -m pip install \
      --no-cache-dir --user --upgrade certifi==2026.10.19 virtualenv==21.14.13 filelock==4.2.1 && \
    PYTHONUSERBASE=/app/.local /usr/bin/python3.12 -m pip check
# hadolint ignore=DL3066
USER 1001
