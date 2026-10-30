#!/usr/bin/env bash
set -euo pipefail
name="${1:?An image name is required}"
case "$name" in
  awx|awx-ee|receptor|ansible-rulebook|galaxy-ng|gateway|eda-controller|eda-podman|eda-decision-environment) ;;
  *) echo "Unknown bundle image: $name" >&2; exit 1 ;;
esac
mkdir -p bundle-reports
if [[ "$name" == gateway ]]; then
  exit 0
fi
if [[ "$name" == receptor ]]; then
  docker build -f images/receptor-runtime/Dockerfile --build-arg BASE_IMAGE=receptor:devel \
    --build-arg VERSION="1.6.9.dev1+g$GITHUB_SHA" -t receptor:patched .upstream/receptor
  docker tag receptor:patched receptor:devel
fi
runtime_user="$(docker image inspect --format '{{.Config.User}}' "$name:devel")"
docker build -f images/runtime-security/OS.Dockerfile \
  --build-arg BASE_IMAGE="$name:devel" --build-arg RUNTIME_USER="${runtime_user:-root}" \
  -t "$name:os-patched" images/runtime-security
docker tag "$name:os-patched" "$name:devel"
docker build -f images/rpm-security/Runtime.Dockerfile \
  --build-arg BASE_IMAGE="$name:devel" --build-arg RUNTIME_USER="${runtime_user:-root}" \
  -t "$name:rpm-patched" bundle-reports/rpm-security
docker tag "$name:rpm-patched" "$name:devel"
docker build -f images/runtime-security/Finalize.Dockerfile \
  --build-arg BASE_IMAGE="$name:devel" --build-arg RUNTIME_USER="${runtime_user:-root}" \
  -t "$name:finalized" images/runtime-security
docker tag "$name:finalized" "$name:devel"

case "$name" in
  awx) python=/var/lib/awx/venv/awx/bin/python ;;
  galaxy-ng) python=/venv/bin/python ;;
  eda-controller) python=/app/venv/bin/python ;;
esac
if [[ "$name" == awx || "$name" == galaxy-ng || "$name" == eda-controller ]]; then
  read -r revision version < <(
    docker run --rm --entrypoint "$python" "$name:devel" -c \
      'import importlib.metadata as m,json; d=m.distribution("django-ansible-base"); print(json.loads(d.read_text("direct_url.json"))["vcs_info"]["commit_id"], d.version.split("+")[0]+"+aax.3")'
  )
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] || {
    echo "Missing exact DAB source revision for $name" >&2
    exit 1
  }
  jq -n --arg service "$name" --arg revision "$revision" --arg version "$version" \
    '{service: $service, repository: "https://github.com/ansible/django-ansible-base", revision: $revision, version: $version}' \
    > "bundle-reports/$name-dab-source.json"
  docker build --build-arg DAB_REVISION="$revision" --build-arg DAB_VERSION="$version" \
    -t "aax/dab-security:$name" images/dab-security
fi
for entry in \
  'awx /var/lib/awx/venv/awx/bin/python 1000 awx' \
  'awx /usr/bin/python3.12 1000 awx-system' \
  'awx-ee /usr/bin/python3.12 1000 awx-ee' \
  'galaxy-ng /venv/bin/python galaxy galaxy' \
  'eda-controller /app/venv/bin/python 1001 eda'; do
  read -r service python runtime_user requirements <<< "$entry"
  [[ "$service" == "$name" ]] || continue
  docker build --build-arg BASE_IMAGE="$name:devel" --build-arg PYTHON="$python" \
    --build-arg REQUIREMENTS="requirements-$requirements.txt" --build-arg RUNTIME_USER="$runtime_user" \
    -t "$name:python-patched" images/runtime-security
  docker tag "$name:python-patched" "$name:devel"
done
case "$name" in
  awx)
    docker build -f images/runtime-security/DAB.Dockerfile --build-arg BASE_IMAGE=awx:devel \
      --build-arg DAB_IMAGE=aax/dab-security:awx -t awx:patched images/runtime-security
    ;;
  awx-ee)
    docker build --build-arg BASE_IMAGE=awx-ee:devel --build-arg RECEPTOR_IMAGE=receptor:devel \
      -t awx-ee:patched images/awx-ee-runtime
    ;;
  eda-controller)
    docker build -f images/runtime-security/EDA.Dockerfile --build-arg BASE_IMAGE=eda-controller:devel \
      --build-arg DAB_IMAGE=aax/dab-security:eda-controller -t eda-controller:patched images/runtime-security
    ;;
  galaxy-ng)
    docker build --build-arg BASE_IMAGE=galaxy-ng:devel --build-arg DAB_IMAGE=aax/dab-security:galaxy-ng \
      -t galaxy-ng:patched images/hub-security
    ;;
  ansible-rulebook)
    docker build --build-arg BASE_IMAGE=ansible-rulebook:devel \
      -t ansible-rulebook:patched images/drools-runtime
    ;;
  eda-decision-environment)
    docker build -f images/eda-decision-environment/Security.Dockerfile \
      -t eda-decision-environment:patched images/runtime-security
    ;;
  receptor|eda-podman) exit 0 ;;
esac
docker tag "$name:patched" "$name:devel"
