#!/usr/bin/env bash
set -euo pipefail
source="${1:?A Galaxy source directory is required}"
patches="${2:?A patch directory is required}"
if [[ -f "$source/setup.py" ]]; then
    patch="$patches/galaxy.patch"
elif [[ -f "$source/pyproject.toml" ]]; then
    patch="$patches/galaxy-pyproject.patch"
else
    echo "No supported Galaxy packaging metadata in $source" >&2
    exit 1
fi
git -C "$source" apply --check "$patch"
git -C "$source" apply "$patch"
