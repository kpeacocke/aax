#!/bin/sh
set -eu
mkdir -p /output/packages /output/provenance
cd /source
version="$(dpkg-query -W -f='${Version}' openssh-client)"
apt-get source "openssh=$version"
directory="$(find . -mindepth 1 -maxdepth 1 -type d -name 'openssh-*')"
test -n "$directory"
cp ./*.dsc ./*.orig.tar.* ./*.debian.tar.* /output/provenance/
printf '%s\n' "$version" > /output/provenance/vendor-version
cp /patches/client-lifetime.patch /output/provenance/
cd "$directory"
export QUILT_PATCH_OPTS=--fuzz=0
quilt import -P aax-client-lifetime.patch /patches/client-lifetime.patch
quilt push
dch --newversion "${version}+aax.1" --distribution trixie --force-distribution \
    'Backport upstream e8bdfb151a356 for CVE-2026-60002 client state lifetime.'
DEB_BUILD_OPTIONS=parallel=2 dpkg-buildpackage -b -Pnoudeb,pkg.openssh.nognome -uc -us
cp ../openssh-client_*.deb /output/packages/
cp ../*.buildinfo ../*.changes /output/provenance/
dpkg -i /output/packages/*.deb
