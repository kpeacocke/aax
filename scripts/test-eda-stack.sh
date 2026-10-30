#!/usr/bin/env bash
set -euo pipefail

: "${EDA_TEST_IMAGE:?An exact scanned controller image is required}"
: "${EDA_TEST_PODMAN_IMAGE:?An exact scanned Podman image is required}"
: "${EDA_TEST_DECISION_IMAGE:?An exact scanned decision image is required}"
: "${EDA_TEST_GIT_REF:?An immutable published Git revision is required}"
: "${EDA_TEST_SECRET:?An ephemeral secret is required}"

project="aax-eda-acceptance-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
compose=(docker compose --env-file /dev/null -p "$project" -f tests/eda-compose.yml)
mkdir -p bundle-reports
cleanup() {
  result=$?
  "${compose[@]}" logs --no-color > bundle-reports/eda-controller-acceptance.log 2>&1 || result=1
  "${compose[@]}" down --volumes --remove-orphans || result=1
  exit "$result"
}
trap cleanup EXIT

"${compose[@]}" up -d --wait --wait-timeout 240
"${compose[@]}" exec -T controller aap-eda-manage shell -c \
  'from django.contrib.auth import get_user_model; u=get_user_model().objects.create_superuser(username="aax_acceptance", password=None); assert u.is_superuser'

# Pull the exact scanned manifest; Docker archives do not preserve RepoDigests.
"${compose[@]}" exec -T podman podman pull "$EDA_TEST_DECISION_IMAGE"
runner=(/app/venv/bin/python /acceptance/test-eda-activation.py
  --local-user aax_acceptance --state-file /var/log/eda/acceptance.json)
"${compose[@]}" exec -T controller "${runner[@]}" --phase prepare \
  --prefix "$project" --git-ref "$EDA_TEST_GIT_REF" \
  --decision-image "$EDA_TEST_DECISION_IMAGE"
"${compose[@]}" exec -T controller "${runner[@]}" --phase check
"${compose[@]}" restart activation
"${compose[@]}" exec -T controller "${runner[@]}" --phase check

# Preserve volumes and enabled activation state; require fresh logs after redeploy.
"${compose[@]}" stop
"${compose[@]}" up -d --force-recreate --wait --wait-timeout 240
"${compose[@]}" exec -T controller "${runner[@]}" --phase check
"${compose[@]}" exec -T controller cat /var/log/eda/acceptance.json \
  > bundle-reports/eda-controller-acceptance.json
echo "AAX_CONTROLLER_ACTIVATION_RECOVERY_PASSED"
