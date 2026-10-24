ARG RECEPTOR_IMAGE=receptor:devel
ARG BASE_IMAGE=awx-ee:python-patched
# hadolint ignore=DL3006
FROM ${RECEPTOR_IMAGE} AS receptor
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
RUN /usr/bin/python3.12 -m pip install --no-cache-dir \
      git+https://github.com/ansible/ansible-runner.git@c3e8cdb24f784a70328f1bfb54eb9c886148acef && \
    ansible-galaxy collection install -p /usr/share/ansible/collections \
      ansible.posix:2.2.2 community.docker:5.4.0 \
      community.library_inventory_filtering_v1:1.1.5 && \
    /usr/bin/python3.12 -m pip check
COPY --from=receptor /usr/bin/receptor /usr/bin/receptor
ENV AAX_BAKED_EXECUTOR_DEPENDENCIES=true
# hadolint ignore=DL3066
USER 1000
