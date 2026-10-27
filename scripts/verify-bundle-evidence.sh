#!/usr/bin/env bash
set -euo pipefail
names=(awx awx-ee receptor ansible-rulebook galaxy-ng gateway eda-controller eda-podman eda-decision-environment)
[[ "$(find candidate-maps/gated -name '*.json' -type f | wc -l)" -eq "${#names[@]}" ]]
[[ "$(find candidate-maps/raw -name '*.json' -type f | wc -l)" -eq "${#names[@]}" ]]
[[ "$(find candidate-maps/tools -name '*.json' -type f | wc -l)" -eq 2 ]]
jq -e --arg aax "$GITHUB_SHA" --arg tag "$IMAGE_TAG" '
  .aax_revision == $aax and .image_tag == $tag and
  ([.sources[].name] | sort) == ["ansible-rulebook","awx","awx-ee","galaxy-ng","receptor"] and
  all(.sources[]; .revision | test("^[0-9a-f]{40}$"))
' bundle-reports/sources.json >/dev/null
for name in "${names[@]}"; do
  bash scripts/bundle-candidate.sh verify "$name" raw
  bash scripts/bundle-candidate.sh verify "$name" gated
  descriptor="candidate-maps/gated/$name.json"
  cmp "$descriptor" "bundle-reports/$name-gate.json"
  image_id="$(jq -r .image_id "$descriptor")"
  jq -e --arg id "$image_id" '.Metadata.ImageID == $id' "bundle-reports/$name.json" >/dev/null
  jq -e --arg id "$image_id" '.source.target.imageID == $id' "bundle-reports/$name-grype.json" >/dev/null
  jq -e '.bomFormat == "CycloneDX" and (.components | type == "array" and length > 0)' \
    "bundle-reports/$name.cdx.json" >/dev/null
  for report in "$name.sarif" "$name-grype.sarif"; do
    jq -e '.version == "2.1.0" and (.runs | type == "array" and length > 0) and
      all(.runs[]; .tool.driver.name | type == "string" and length > 0)' \
      "bundle-reports/$report" >/dev/null
  done
  bash scripts/check-vulnerability-reports.sh "bundle-reports/$name.json" "bundle-reports/$name-grype.json"
done
for name in awx galaxy-ng eda-controller; do
  jq -e --arg service "$name" '
    .service == $service and .repository == "https://github.com/ansible/django-ansible-base" and
    (.revision | type == "string" and test("^[0-9a-f]{40}$")) and
    (.version | type == "string" and endswith("+aax.2"))
  ' "bundle-reports/$name-dab-source.json" >/dev/null
done
for name in pip-security go-security; do
  bash scripts/bundle-candidate.sh verify "$name" tools
done
test -s native-rpms.tar.gz
tar -xzf native-rpms.tar.gz -C bundle-reports
test -s bundle-reports/rpm-security/install.sh
for package in $(jq -er 'keys[]' images/rpm-security/sources.json); do
  directory="bundle-reports/rpm-security/packages/$package"
  checksum="$(jq -er --arg package "$package" '.[$package].sha256' images/rpm-security/sources.json)"
  echo "$checksum  $directory/signed-source.src.rpm" | sha256sum --check -
  grep -Fq 'digests signatures OK' "$directory/source-signature.txt"
  test -n "$(find "$directory/srpms" -name '*.rpm' -size +0c -print -quit)"
  test -n "$(find "$directory/rpms" -name '*.rpm' -size +0c -print -quit)"
done
jq -s -e '.[0] == {podman: .[1], decision: .[2]}' bundle-reports/runtime-gate.json \
  candidate-maps/gated/eda-podman.json candidate-maps/gated/eda-decision-environment.json >/dev/null
grep -Fq AAX_DECISION_SECURITY_SMOKE_PASSED bundle-reports/eda-rulebook-smoke.log
test -s bundle-reports/nested-runtime.log
