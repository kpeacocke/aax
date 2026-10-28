#!/usr/bin/env bash
set -euo pipefail
output="${1:?An output directory is required}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base_image="${RPM_BUILD_BASE_IMAGE:-awx-ee:os-patched}"
context="$root/images/rpm-security"
packages="$(jq -er 'keys[]' "$context/sources.json")"
mkdir -p "$output/packages" "$output/rpms" "$output/logs"
cp "$context/Dockerfile" "$output/Artifacts.Dockerfile"
printf '\nCOPY --from=builder /build/source.src.rpm /signed-source.src.rpm\n' \
    >> "$output/Artifacts.Dockerfile"
build_logged() {
    local log="$1"
    shift
    echo "Building RPM security stage; full log: $log"
    if docker build --progress=plain "$@" > "$log" 2>&1; then
        tail -n 10 "$log"
    else
        local result=$?
        tail -n 100 "$log" >&2
        return "$result"
    fi
}
build_logged "$output/logs/bootstrap.log" \
    --target builder-base --build-arg BASE_IMAGE="$base_image" \
    -t aax/rpm-builder:bootstrap "$context"
build_logged "$output/logs/compiler.log" -f "$context/Go.Dockerfile" \
    --build-arg BASE_IMAGE=aax/rpm-builder:bootstrap \
    -t aax/go-security:devel "$context"
if [[ "${RPM_RETAIN_COMPILER:-false}" == true ]]; then
    docker tag aax/go-security:devel go-security:devel
    bash "$root/scripts/bundle-candidate.sh" push go-security tools
fi
while IFS= read -r package; do
    build_logged "$output/logs/$package.log" -f "$output/Artifacts.Dockerfile" \
        --build-arg BASE_IMAGE="$base_image" \
        --build-arg GO_IMAGE=aax/go-security:devel --build-arg GO_ROOT=/go \
        --build-arg PACKAGE="$package" \
        --output "type=local,dest=$output/packages/$package" "$context"
    test -s "$output/packages/$package/signed-source.src.rpm"
    cp "$output/packages/$package/rpms/"*.rpm "$output/rpms/"
done <<< "$packages"
cp "$context/install.sh" "$output/install.sh"
