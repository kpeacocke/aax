#!/usr/bin/env bash
set -euo pipefail
output="${1:?An output directory is required}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base_image="${RPM_BUILD_BASE_IMAGE:-awx-ee:os-patched}"
context="$root/images/rpm-security"
packages="$(jq -er 'keys[]' "$context/sources.json")"
mkdir -p "$output/packages" "$output/rpms"
docker build --target builder-base --build-arg BASE_IMAGE="$base_image" \
    -t aax/rpm-builder:bootstrap "$context"
docker build -f "$context/Go.Dockerfile" \
    --build-arg BASE_IMAGE=aax/rpm-builder:bootstrap \
    -t aax/go-security:devel "$context"
while IFS= read -r package; do
    docker build --build-arg BASE_IMAGE="$base_image" \
        --build-arg GO_IMAGE=aax/go-security:devel --build-arg GO_ROOT=/go \
        --build-arg PACKAGE="$package" \
        --output "type=local,dest=$output/packages/$package" "$context"
    cp "$output/packages/$package/rpms/"*.rpm "$output/rpms/"
done <<< "$packages"
cp "$context/install.sh" "$output/install.sh"
