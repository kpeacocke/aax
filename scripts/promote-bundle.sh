#!/usr/bin/env bash
set -euo pipefail
# Check every receipt before the first registry write, even if invoked outside Actions.
bash scripts/verify-bundle-evidence.sh
[[ "$GITHUB_REF" == refs/heads/main ]] || {
  echo "Branch validation retains candidates; deployment tags are main-only."
  exit 0
}
owner="$(printf '%s' "$IMAGE_OWNER" | tr '[:upper:]' '[:lower:]')"
names=(awx awx-ee receptor ansible-rulebook galaxy-ng gateway eda-controller eda-podman eda-decision-environment pulp)
for name in "${names[@]}"; do
  source="$name"
  [[ "$name" != pulp ]] || source=galaxy-ng
  descriptor="candidate-maps/gated/$source.json"
  reference="$(jq -r '.repository + "@" + .digest' "$descriptor")"
  target="$REGISTRY/$owner/aax-$name:$IMAGE_TAG"
  docker buildx imagetools create --prefer-index=false --tag "$target" "$reference"
  docker buildx imagetools inspect "$target" --format '{{json .Manifest}}' \
    > "bundle-reports/$name-manifest.json"
  [[ "$(jq -r .digest "bundle-reports/$name-manifest.json")" == "$(jq -r .digest "$descriptor")" ]]
done
# Do not move any mutable tag until all immutable copies have been verified.
if [[ "$PUSH_MUTABLE" == true ]]; then
  for name in "${names[@]}"; do
    source="$name"
    [[ "$name" != pulp ]] || source=galaxy-ng
    reference="$(jq -r '.repository + "@" + .digest' "candidate-maps/gated/$source.json")"
    target="$REGISTRY/$owner/aax-$name:devel"
    docker buildx imagetools create --prefer-index=false --tag "$target" "$reference"
    actual="$(docker buildx imagetools inspect "$target" --format '{{json .Manifest}}' | jq -er .digest)"
    [[ "$actual" == "${reference##*@}" ]]
  done
fi
echo "Published bundle: \`$IMAGE_TAG\`" >> "$GITHUB_STEP_SUMMARY"
