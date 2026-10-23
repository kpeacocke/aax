#!/usr/bin/env bash
set -euo pipefail
directory="${1:?A directory of rebuilt RPMs is required}"
set --
for file in "$directory"/*.rpm; do
    name="$(rpm -qp --queryformat '%{NAME}' "$file")"
    if rpm -q "$name" >/dev/null 2>&1; then
        set -- "$@" "$file"
    fi
done
if [[ "$#" -eq 0 ]]; then
    echo "No applicable AAX security RPMs were built for this image" >&2
    exit 1
fi
rpm --upgrade "$@"
for file in "$@"; do
    name="$(rpm -qp --queryformat '%{NAME}' "$file")"
    expected="$(rpm -qp --queryformat '%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}' "$file")"
    actual="$(rpm -q --queryformat '%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}' "$name")"
    if [[ "$actual" != "$expected" ]]; then
        echo "AAX RPM upgrade did not install $name: expected $expected, found $actual" >&2
        exit 1
    fi
done
rpm --verify --all --nofiles --noscripts
