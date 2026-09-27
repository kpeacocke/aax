#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export AWX_IMAGE_REPOSITORY="${AWX_IMAGE_REPOSITORY:-aax/awx}"
export AWX_VERSION="${AWX_VERSION:-devel}"
export AWX_EE_IMAGE_REPOSITORY="${AWX_EE_IMAGE_REPOSITORY:-aax/awx-ee}"
export AWX_EE_VERSION="${AWX_EE_VERSION:-devel}"
export RECEPTOR_IMAGE_REPOSITORY="${RECEPTOR_IMAGE_REPOSITORY:-aax/receptor}"
export RECEPTOR_VERSION="${RECEPTOR_VERSION:-devel}"
export AWX_REDIS_VOLUME="${AWX_REDIS_VOLUME:-aax_devel_awx_redis_data}"
export DEVEL_IMAGE_TAG="${DEVEL_IMAGE_TAG:-devel}"
export DEVEL_AWX_IMAGE="${DEVEL_AWX_IMAGE:-aax/awx}"
export DEVEL_AWX_EE_IMAGE="${DEVEL_AWX_EE_IMAGE:-aax/awx-ee}"
export DEVEL_RECEPTOR_IMAGE="${DEVEL_RECEPTOR_IMAGE:-aax/receptor}"
export DEVEL_GATEWAY_IMAGE="${DEVEL_GATEWAY_IMAGE:-aax/gateway}"
export DEVEL_PULP_IMAGE="${DEVEL_PULP_IMAGE:-aax-pulp}"
export DEVEL_GALAXY_IMAGE="${DEVEL_GALAXY_IMAGE:-aax-galaxy-ng}"
export DEVEL_EDA_IMAGE="${DEVEL_EDA_IMAGE:-aax/eda-controller}"
if [[ "${DEVEL_IMAGE_TAG:-}" == "devel-<commit-sha>" ]]; then
  export DEVEL_IMAGE_TAG=devel
fi

if [[ "$#" -eq 0 ]]; then
  set -- up -d
fi

exec docker compose \
  -f docker-compose.yml \
  -f docker-compose.devel.yml \
  --profile controller \
  "$@"
