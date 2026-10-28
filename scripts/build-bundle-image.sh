#!/usr/bin/env bash
set -euo pipefail
name="${1:?An image name is required}"
case "$name" in
  awx)
    cd .upstream/awx
    version="24.6.1.dev1+g$GITHUB_SHA"
    ansible-playbook -e ansible_python_interpreter=python3 tools/ansible/dockerfile.yml \
      -e dockerfile_name=Dockerfile.devel -e build_dev=False -e headless=True
    grep -q '^ENV SETUPTOOLS_SCM_PRETEND_VERSION=' Dockerfile.devel || \
      sed -i "/^ARG SETUPTOOLS_SCM_PRETEND_VERSION/a ENV SETUPTOOLS_SCM_PRETEND_VERSION=\${SETUPTOOLS_SCM_PRETEND_VERSION}" Dockerfile.devel
    docker buildx build --load -f Dockerfile.devel -t awx:devel \
      --build-arg VERSION="$version" --build-arg SETUPTOOLS_SCM_PRETEND_VERSION="$version" .
    cd ../..
    docker build --build-arg AWX_BASE_IMAGE=awx --build-arg AWX_BASE_TAG=devel \
      -t awx:with-ui images/awx-ui-runtime
    docker tag awx:with-ui awx:devel
    ;;
  awx-ee)
    cd .upstream/awx-ee
    ansible-builder build -v3 -t awx-ee:devel --container-runtime=docker
    ;;
  receptor)
    cd .upstream/receptor
    rm -f .container-flag-*
    PATH="$GITHUB_WORKSPACE/.venv/bin:$PATH" \
      make VERSION="1.6.9.dev1+g$GITHUB_SHA" container REPO=receptor TAG=devel CONTAINERCMD=docker
    ;;
  ansible-rulebook)
    cd .upstream/ansible-rulebook
    grep -q '^ENV SETUPTOOLS_SCM_PRETEND_VERSION=' Dockerfile || \
      sed -i "/^ARG SETUPTOOLS_SCM_PRETEND_VERSION/a ENV SETUPTOOLS_SCM_PRETEND_VERSION=\${SETUPTOOLS_SCM_PRETEND_VERSION}" Dockerfile
    docker buildx build --load -t ansible-rulebook:devel \
      --build-arg SETUPTOOLS_SCM_PRETEND_VERSION="1.0.0.dev1+g$GITHUB_SHA" .
    ;;
  galaxy-ng)
    cd .upstream/galaxy-ng
    docker buildx build --load -t galaxy-ng:devel --build-arg GIT_COMMIT="$GITHUB_SHA" .
    cd ../..
    docker build --build-arg BASE_IMAGE=galaxy-ng:devel -t galaxy-ng:runtime images/galaxy-runtime
    docker tag galaxy-ng:runtime galaxy-ng:devel
    ;;
  gateway) docker buildx build --load -t gateway:devel images/gateway ;;
  eda-controller) docker buildx build --load -t eda-controller:devel images/eda-server ;;
  eda-podman)
    docker buildx build --load \
      --build-arg BASE_IMAGE=quay.io/centos/centos@sha256:6f8045fc4f552544d8a401d61848bafc8d06ca7c11897c5b54a2c37fc419a20a \
      -t eda-podman:devel images/eda-podman
    ;;
  eda-decision-environment)
    docker buildx build --load -t eda-decision-environment:devel images/eda-decision-environment
    ;;
  *) echo "Unknown bundle image: $name" >&2; exit 1 ;;
esac
