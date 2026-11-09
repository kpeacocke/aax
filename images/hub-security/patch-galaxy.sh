#!/usr/bin/env bash
set -euo pipefail
source="${1:?A Galaxy source directory is required}"
patches="${2:?A patch directory is required}"
version="${3:?An exact verified DAB version is required}"
if [[ ! "$version" =~ ^[0-9][0-9A-Za-z.]*\+aax\.3$ ]]; then
    echo "An exact verified DAB version with the current source patch is required" >&2
    exit 1
fi
if [[ -f "$source/setup.py" ]]; then
    patch="$patches/galaxy.patch"
elif [[ -f "$source/pyproject.toml" ]]; then
    patch="$patches/galaxy-pyproject.patch"
else
    echo "No supported Galaxy packaging metadata in $source" >&2
    exit 1
fi
sed "s/@AAX_DAB_VERSION@/$version/g" "$patch" | git -C "$source" apply --check -
sed "s/@AAX_DAB_VERSION@/$version/g" "$patch" | git -C "$source" apply -
