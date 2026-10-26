ARG BASE_IMAGE=quay.io/ansible/ansible-rulebook@sha256:68bb8aae9ad8be20863a6d42a97cea8a4865d393e1ed63f29259162e5e6108dd
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="AAX EDA decision environment" \
      org.opencontainers.image.description="Digest-pinned ansible-rulebook runtime with ansible.eda event sources"

RUN ansible-galaxy collection list ansible.eda > /tmp/eda-collections && \
    grep -Eq 'ansible\.eda[[:space:]]+2\.13\.0' /tmp/eda-collections && \
    rm /tmp/eda-collections
