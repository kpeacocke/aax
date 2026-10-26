#!/bin/sh
set -eu

if command -v rpm >/dev/null 2>&1; then
    packages="$(rpm -qa --qf '%{NAME}\n')"
    if printf '%s\n' "$packages" | grep -qx python3.12-setuptools; then
        # Runtime applications use their maintained virtualenv, not this build helper.
        rpm --erase python3.12-setuptools
    fi
fi
