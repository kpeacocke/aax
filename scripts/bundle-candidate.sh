#!/usr/bin/env bash
set -euo pipefail

action="${1:?An action is required}"
name="${2:?An image name is required}"
stage="${3:?A candidate stage is required}"
[[ "$name" =~ ^[a-z][a-z0-9-]*$ && "$stage" =~ ^(raw|tools|gated)$ ]]
owner="$(printf '%s' "$IMAGE_OWNER" | tr '[:upper:]' '[:lower:]')"
repository="$REGISTRY/$owner/aax-$name"
tag="candidate-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT-$stage"
descriptor="candidate-maps/$stage/$name.json"

case "$action" in
  push)
    mkdir -p "candidate-maps/$stage"
    image_id="$(docker image inspect --format '{{.Id}}' "$name:devel")"
    [[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ ]]
    docker tag "$name:devel" "$repository:$tag"
    docker push "$repository:$tag"
    manifest="$(docker buildx imagetools inspect "$repository:$tag" --format '{{json .Manifest}}')"
    digest="$(jq -er '.digest | select(test("^sha256:[0-9a-f]{64}$"))' <<< "$manifest")"
    config="$(docker buildx imagetools inspect --raw "$repository@$digest" | jq -er '.config.digest')"
    [[ "$image_id" == "$config" ]]
    jq -n --arg name "$name" --arg stage "$stage" --arg repository "$repository" \
      --arg digest "$digest" --arg image_id "$image_id" --arg aax "$GITHUB_SHA" \
      --arg run "$GITHUB_RUN_ID" --arg attempt "$GITHUB_RUN_ATTEMPT" \
      '{name: $name, stage: $stage, repository: $repository, digest: $digest,
        image_id: $image_id, aax_revision: $aax, run_id: $run, run_attempt: $attempt}' \
      > "$descriptor"
    ;;
  verify|pull)
    jq -e --arg name "$name" --arg stage "$stage" --arg repository "$repository" \
      --arg aax "$GITHUB_SHA" --arg run "$GITHUB_RUN_ID" --arg attempt "$GITHUB_RUN_ATTEMPT" '
      .name == $name and .stage == $stage and .repository == $repository and
      .aax_revision == $aax and .run_id == $run and .run_attempt == $attempt and
      (.digest | type == "string" and test("^sha256:[0-9a-f]{64}$")) and
      (.image_id | type == "string" and test("^sha256:[0-9a-f]{64}$"))
    ' "$descriptor" >/dev/null
    if [[ "$action" == pull ]]; then
      reference="$(jq -r '.repository + "@" + .digest' "$descriptor")"
      docker pull "$reference"
      docker tag "$reference" "$name:devel"
      [[ "$(docker image inspect --format '{{.Id}}' "$name:devel")" == \
        "$(jq -r .image_id "$descriptor")" ]]
    fi
    ;;
  *) echo "Unknown candidate action: $action" >&2; exit 1 ;;
esac
