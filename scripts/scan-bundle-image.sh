#!/usr/bin/env bash
set -euo pipefail
name="${1:?An image name is required}"
bash scripts/bundle-candidate.sh verify "$name" gated
descriptor="candidate-maps/gated/$name.json"
reference="$(jq -r '.repository + "@" + .digest' "$descriptor")"
image_id="$(jq -r .image_id "$descriptor")"
digest="$(jq -r .digest "$descriptor")"
mkdir -p bundle-reports bundle-sarif
trivy image --image-src docker --scanners vuln --timeout 15m --format json \
  --output "bundle-reports/$name.json" "$reference"
trivy convert --format sarif --output "bundle-reports/$name.sarif" "bundle-reports/$name.json"
trivy image --image-src docker --scanners vuln --format cyclonedx --timeout 15m \
  --output "bundle-reports/$name.cdx.json" "$reference"
"$RUNNER_TEMP/grype" "docker:$reference" --platform linux/amd64 \
  -o "json=bundle-reports/$name-grype.json" -o "sarif=bundle-reports/$name-grype.sarif"
jq -e --arg id "$image_id" --arg digest "$digest" \
  '.Metadata.ImageID == $id or .Metadata.ImageID == $digest' "bundle-reports/$name.json"
jq -e --arg id "$image_id" '.source.target.imageID == $id' "bundle-reports/$name-grype.json"
bash scripts/check-vulnerability-reports.sh "bundle-reports/$name.json" "bundle-reports/$name-grype.json"
cp "$descriptor" "bundle-reports/$name-gate.json"
