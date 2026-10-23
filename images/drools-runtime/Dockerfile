ARG BASE_IMAGE=ansible-rulebook:devel
FROM maven:3.9.11-eclipse-temurin-17 AS builder
WORKDIR /source
ARG DROOLS_REVISION=541a88af7e06949dcd574718b593d9dd5681e8ae
RUN git init && git remote add origin https://github.com/kiegroup/drools-ansible-rulebook-integration.git && \
    git fetch --depth 1 origin "${DROOLS_REVISION}" && git checkout --detach FETCH_HEAD
COPY jackson.patch /tmp/jackson.patch
RUN git apply /tmp/jackson.patch && \
    mvn -B -ntp -pl drools-ansible-rulebook-integration-runtime -am package
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
COPY --from=builder /source/drools-ansible-rulebook-integration-runtime/target/drools-ansible-rulebook-integration-runtime-2.0.1-SNAPSHOT-HA.jar /usr/local/lib/python3.12/site-packages/drools/jars/drools-ansible-rulebook-integration-runtime-2.0.1-SNAPSHOT-HA.jar
# hadolint ignore=DL3066
USER 1001
