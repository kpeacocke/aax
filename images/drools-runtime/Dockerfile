ARG BASE_IMAGE=ansible-rulebook:devel
FROM maven:3.9-eclipse-temurin-26 AS builder
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
WORKDIR /source
ARG DROOLS_REVISION=541a88af7e06949dcd574718b593d9dd5681e8ae
RUN git init && git remote add origin https://github.com/kiegroup/drools-ansible-rulebook-integration.git && \
    git fetch --depth 1 origin "${DROOLS_REVISION}" && git checkout --detach FETCH_HEAD
COPY jackson.patch /tmp/jackson.patch
RUN git apply /tmp/jackson.patch && \
    mvn -B -ntp -pl drools-ansible-rulebook-integration-runtime -am package
ARG TARGETARCH
RUN case "${TARGETARCH}" in \
      amd64) arch=x64; checksum=9f41bf88c7900c7097444a1bdeb84146ae692bc08842490ab098063c74bf9a8a ;; \
      arm64) arch=aarch64; checksum=1114f09d6174f54270c3117410b5e4022b43ebc0b43b751af08b927c55ed7bb5 ;; \
      *) echo "Unsupported Java runtime architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl --fail --location --retry 3 --max-time 120 \
      "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.21%2B9/OpenJDK17U-jre_${arch}_linux_hotspot_17.0.21_9.tar.gz" \
      --output /tmp/jre.tar.gz && \
    echo "${checksum}  /tmp/jre.tar.gz" | sha256sum --check - && \
    mkdir /jre && tar -xzf /tmp/jre.tar.gz --strip-components=1 -C /jre && \
    rm /tmp/jre.tar.gz
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
# hadolint ignore=DL3066
USER root
ENV JAVA_HOME=/opt/java/openjdk \
    LD_LIBRARY_PATH=/opt/java/openjdk/lib/server \
    PATH="/opt/java/openjdk/bin:${PATH}"
RUN dnf -y --setopt=clean_requirements_on_remove=False remove 'java-17-openjdk*' && \
    dnf clean all
COPY --from=builder /jre /opt/java/openjdk
COPY --from=builder /source/drools-ansible-rulebook-integration-runtime/target/drools-ansible-rulebook-integration-runtime-2.0.1-SNAPSHOT-HA.jar /usr/local/lib/python3.12/site-packages/drools/jars/drools-ansible-rulebook-integration-runtime-2.0.1-SNAPSHOT-HA.jar
# hadolint ignore=DL3066
USER 1001
RUN java -version && \
    python3.12 -c 'from drools.ruleset import _make_jpy_instance; assert _make_jpy_instance()'
