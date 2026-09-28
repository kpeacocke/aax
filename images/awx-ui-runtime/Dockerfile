ARG AWX_BASE_IMAGE=ghcr.io/kpeacocke/aax-awx
ARG AWX_BASE_TAG=devel-cb8ba124a551f58b5499752bbad33dc4d9a66f48
FROM node:22-bookworm AS ui
WORKDIR /src
# Last standalone AWX webpack configuration before the upstream platform redesign.
ARG UI_REVISION=b512f07205f2be38d29dc245e955e66e64248ae3
RUN git init && git remote add origin https://github.com/ansible/ansible-ui.git && git fetch --depth 1 origin "$UI_REVISION" && git checkout --detach FETCH_HEAD
RUN npm ci --ignore-scripts
RUN PRODUCT=AWX PUBLIC_PATH=/static/awx/ ROUTE_PREFIX=/ NODE_OPTIONS=--max-old-space-size=4096 npm run build:awx && mv build/awx/index.html build/awx/index_awx.html

FROM ${AWX_BASE_IMAGE}:${AWX_BASE_TAG}
USER root
COPY --from=ui /src/build/awx /tmp/aax-ui
RUN set -eu; \
    awx_dir=$(/var/lib/awx/venv/awx/bin/python -c 'import awx,pathlib; print(pathlib.Path(awx.__file__).parent)'); \
    mkdir -p "$awx_dir/ui/build/awx"; \
    cp -a /tmp/aax-ui/. "$awx_dir/ui/build/awx/"; \
    AWX_MODE=defaults SKIP_SECRET_KEY_CHECK=yes SKIP_PG_VERSION_CHECK=yes AWX_SKIP_CREDENTIAL_TYPES_DISCOVER=yes /var/lib/awx/venv/awx/bin/awx-manage collectstatic --noinput --clear; \
    test -s "$awx_dir/ui/build/awx/index_awx.html"; \
    test -d /var/lib/awx/public/static/awx; \
    rm -rf /tmp/aax-ui
USER 1000
