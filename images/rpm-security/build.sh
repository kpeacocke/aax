#!/usr/bin/env bash
set -euo pipefail
package="$(cat /build/package)"
rpmbuild -ba --define '_topdir /build/rpmbuild' \
    --define '_smp_mflags -j2' --define 'vendor AAX' \
    --define 'packager AAX downstream source rebuild' \
    "/build/rpmbuild/SPECS/$package.spec" 2>&1 | tee /build/output/build.log
find /build/rpmbuild/RPMS -name '*.rpm' -exec cp -t /build/output/rpms {} +
find /build/rpmbuild/SRPMS -name '*.rpm' -exec cp -t /build/output/srpms {} +
test -n "$(find /build/output/rpms -name '*.rpm' -print -quit)"
test -n "$(find /build/output/srpms -name '*.rpm' -print -quit)"
