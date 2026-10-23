ARG BASE_IMAGE=awx-ee:os-patched
ARG GO_IMAGE=golang:1.27.3
# hadolint ignore=DL3006
FROM ${GO_IMAGE} AS go
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS builder-base
# Build-only stage needs root to install verified build dependencies.
# hadolint ignore=DL3002,DL3066
USER root
# hadolint ignore=DL3041
RUN dnf -y --enablerepo=crb install \
      dnf-plugins-core rpm-build rpmdevtools redhat-rpm-config \
      make gcc gcc-c++ git jq curl-minimal && dnf clean all
ARG GO_ROOT=/usr/local/go
COPY --from=go ${GO_ROOT} /opt/aax-go
COPY go-toolchain.spec /tmp/go-toolchain.spec
RUN rpmbuild -bb --define '_topdir /tmp/go-rpm' /tmp/go-toolchain.spec && \
    dnf -y install /tmp/go-rpm/RPMS/*/aax-go-toolchain-*.rpm && dnf clean all
ENV PATH="/opt/aax-go/bin:${PATH}" GOTOOLCHAIN=local GOROOT=/opt/aax-go
ADD --checksum=sha256:387a8be6b70ecff4949d28778bf8abd06231654283b6e9515afc9305a1391458 https://repo.almalinux.org/almalinux/RPM-GPG-KEY-AlmaLinux-9 /tmp/alma-signing-key
RUN rpm --import /tmp/alma-signing-key /etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial
# hadolint ignore=DL3041
RUN dnf -y --enablerepo=crb install go-rpm-macros python3.12-rpm-macros && dnf clean all
FROM builder-base AS builder
ARG PACKAGE=libevent
COPY sources.json prepare.sh setuptools-unicode.patch setuptools_regression.py \
     go-vendor.sh go-dependencies.json /aax/
RUN bash /aax/prepare.sh "${PACKAGE}"
# Build-only cache retains verified dependencies across source-patch retries.
RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked \
    dnf -y --setopt=keepcache=True --enablerepo=crb builddep /build/rpmbuild/SPECS/*.spec
COPY build.sh /aax/build.sh
RUN bash /aax/build.sh
FROM scratch AS artifacts
COPY --from=builder /build/output/ /
