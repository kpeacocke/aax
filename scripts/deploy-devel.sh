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
export DEVEL_IMAGE_PREFIX="${DEVEL_IMAGE_PREFIX:-aax}"
export DEVEL_IMAGE_TAG="${DEVEL_IMAGE_TAG:-devel}"

if [[ "$#" -eq 0 ]]; then
  set -- up -d
fi

exec docker compose \
  -f docker-compose.yml \
  -f docker-compose.devel.yml \
  --profile controller \
  "$@"
