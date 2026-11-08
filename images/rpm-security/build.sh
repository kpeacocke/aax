#!/usr/bin/env bash
set -euo pipefail
package="$(cat /build/package)"
set --
if [[ "$package" == icu ]]; then
    # ICU's recursive linker inherits unusable jobserver FDs. Avoid that
    # jobserver while retaining LTO with an explicit, bounded worker count.
    set -- --define '_smp_mflags -j1' --define '_lto_cflags -flto=2 -ffat-lto-objects'
fi
rpmbuild -ba --define '_topdir /build/rpmbuild' \
    --define '_smp_mflags -j2' --define 'vendor AAX' \
    --define 'packager AAX downstream source rebuild' \
    "$@" \
    "/build/rpmbuild/SPECS/$package.spec" 2>&1 | tee /build/output/build.log
find /build/rpmbuild/RPMS -name '*.rpm' -exec cp -t /build/output/rpms {} +
find /build/rpmbuild/SRPMS -name '*.rpm' -exec cp -t /build/output/srpms {} +
test -n "$(find /build/output/rpms -name '*.rpm' -print -quit)"
test -n "$(find /build/output/srpms -name '*.rpm' -print -quit)"
