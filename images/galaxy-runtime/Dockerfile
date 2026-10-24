ARG BASE_IMAGE=galaxy-ng:upstream
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
RUN rm -f /app/profiles/dab_jwt/proxy/tmp/main
COPY --chmod=755 entrypoint.py /usr/local/bin/aax-hub-entrypoint
# hadolint ignore=DL3066
USER galaxy
ENTRYPOINT ["/usr/local/bin/aax-hub-entrypoint"]
