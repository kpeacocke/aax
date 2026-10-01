#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_DIR="$ROOT_DIR/.upstream"
REPO_BASE="https://github.com/ansible"

AWX_BRANCH="${AWX_BRANCH:-devel}"
AWX_DAB_REF="${AWX_DAB_REF:-}"
AWX_EE_BRANCH="${AWX_EE_BRANCH:-devel}"
RECEPTOR_BRANCH="${RECEPTOR_BRANCH:-devel}"
RULEBOOK_BRANCH="${RULEBOOK_BRANCH:-main}"
GALAXY_NG_BRANCH="${GALAXY_NG_BRANCH:-main}"

if [[ -z "$AWX_DAB_REF" && "$AWX_BRANCH" == "24.6.1" ]]; then
  AWX_DAB_REF=2024.6.26
fi

mkdir -p "$UPSTREAM_DIR"

resolve_remote_head_branch() {
  local repo_url="$1"
  git ls-remote --symref "$repo_url" HEAD 2>/dev/null | awk '/^ref:/ {print $3}' | sed 's#refs/heads/##' | head -n 1
}

clone_repo() {
  local name="$1"
  local repo="$2"
  local ref="${3:-}"
  local dest="$UPSTREAM_DIR/$name"

  if [[ -d "$dest/.git" ]]; then
    echo "[$name] already present at $dest"
    return
  fi

  local branch_to_use="$ref"
  if [[ -z "$branch_to_use" ]]; then
    branch_to_use="$(resolve_remote_head_branch "$repo")"
  fi

  echo "[$name] cloning $repo${branch_to_use:+ (branch: $branch_to_use)}"
  if [[ -n "$branch_to_use" ]]; then
    git clone --depth 1 --branch "$branch_to_use" "$repo" "$dest"
  else
    git clone --depth 1 "$repo" "$dest"
  fi
}

clone_repo "awx" "$REPO_BASE/awx" "$AWX_BRANCH"
clone_repo "awx-ee" "$REPO_BASE/awx-ee" "$AWX_EE_BRANCH"
clone_repo "receptor" "$REPO_BASE/receptor" "$RECEPTOR_BRANCH"
clone_repo "ansible-rulebook" "$REPO_BASE/ansible-rulebook" "$RULEBOOK_BRANCH"
clone_repo "galaxy-ng" "$REPO_BASE/galaxy_ng" "$GALAXY_NG_BRANCH"

pin_awx_dependencies() {
  local requirements_file="$UPSTREAM_DIR/awx/requirements/requirements_git.txt"

  if [[ -z "$AWX_DAB_REF" ]]; then
    echo "[awx] preserving django-ansible-base ref from AWX $AWX_BRANCH"
    return
  fi

  if [[ ! -f "$requirements_file" ]]; then
    echo "AWX requirements file not found: $requirements_file" >&2
    exit 1
  fi

  python3 - "$requirements_file" "$AWX_DAB_REF" <<'PY'
from pathlib import Path
import sys

requirements_file = Path(sys.argv[1])
dab_ref = sys.argv[2]
contents = requirements_file.read_text()
old_prefix = "django-ansible-base @ git+https://github.com/ansible/django-ansible-base@"
lines = contents.splitlines()
matches = [index for index, line in enumerate(lines) if line.startswith(old_prefix)]
if len(matches) != 1:
    raise SystemExit(
        f"Expected one django-ansible-base dependency in {requirements_file}, "
        f"found {len(matches)}"
    )

index = matches[0]
suffix = lines[index].split("#egg=", 1)[1]
lines[index] = f"{old_prefix}{dab_ref}#egg={suffix}"
requirements_file.write_text("\n".join(lines) + "\n")
PY

  echo "[awx] pinned django-ansible-base to $AWX_DAB_REF"
}

pin_awx_dependencies

cat <<EOF
Upstream source check complete.
Artifacts are in: $UPSTREAM_DIR

Built components should be pinned explicitly before deployment.
This repo remains the compatibility layer around the sources above.

AWX dependency pins:
  - django-ansible-base: $AWX_DAB_REF

Next steps:
  - build AWX from .upstream/awx
  - build awx-ee from .upstream/awx-ee
  - build receptor from .upstream/receptor
  - build ansible-rulebook from .upstream/ansible-rulebook
  - build galaxy-ng from .upstream/galaxy-ng
EOF
