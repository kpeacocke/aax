#!/usr/bin/env bash
set -euo pipefail

image="${1:?An immutable image digest is required}"
category="${2:?A unique publication category is required}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! "$image" =~ @sha256:[0-9a-f]{64}$ ]]; then
  echo "Candidate scans require an immutable sha256 image digest: $image" >&2
  exit 2
fi

mkdir -p image-reports image-sarif
for arch in amd64 arm64; do
  trivy image --scanners vuln --platform "linux/$arch" --timeout 15m \
    --format json --output "image-reports/$arch.json" "$image"
  trivy convert --format sarif --output "image-reports/$arch.sarif" "image-reports/$arch.json"
  jq --exit-status --arg prefix "$category/$arch/" '
    if (.runs | type) != "array" or (.runs | length) == 0 then
      error("Scanner SARIF must contain at least one run")
    else
      .runs |= (to_entries | map(
        .key as $index | .value |
        .automationDetails.id = ($prefix + ($index | tostring) + "/")
      ))
    end
  ' "image-reports/$arch.sarif" > "image-reports/$arch.normalized.tmp"
  mv "image-reports/$arch.normalized.tmp" "image-sarif/$arch.sarif"
done

bash "$root/scripts/check-vulnerability-reports.sh" image-reports/amd64.json image-reports/arm64.json
