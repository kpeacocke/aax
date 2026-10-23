#!/bin/sh
set -eu
if command -v dnf >/dev/null 2>&1; then
    dnf -y upgrade --refresh
    dnf clean all
elif command -v microdnf >/dev/null 2>&1; then
    microdnf -y upgrade --refresh
    microdnf clean all
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get -y upgrade --no-install-recommends
    apt-get clean
    rm -rf /var/lib/apt/lists
else
    echo "No supported OS package manager; security updates cannot be applied" >&2
    exit 1
fi
