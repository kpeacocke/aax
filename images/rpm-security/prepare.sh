#!/usr/bin/env bash
set -euo pipefail
package="${1:?A source package name is required}"
url="$(jq -er --arg name "$package" '.[$name].url' /aax/sources.json)"
checksum="$(jq -er --arg name "$package" '.[$name].sha256' /aax/sources.json)"
release="$(jq -er --arg name "$package" '.[$name].release' /aax/sources.json)"
mkdir -p /build/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} /build/output/{rpms,srpms}
curl --fail --location --retry 3 --connect-timeout 30 --max-time 1800 \
    --output /build/source.src.rpm "$url"
echo "$checksum  /build/source.src.rpm" | sha256sum --check -
rpmkeys --checksig /build/source.src.rpm | tee /build/output/source-signature.txt
grep -Fq 'digests signatures OK' /build/output/source-signature.txt
test "$(rpm -qp --queryformat '%{NAME}' /build/source.src.rpm)" = "$package"
rpm --install --define '_topdir /build/rpmbuild' /build/source.src.rpm
spec="/build/rpmbuild/SPECS/$package.spec"
test "$(grep -c '^Release:' "$spec")" = 1
sed -i -E "s/^Release:.*/Release: $release/" "$spec"
if grep -q '^Vendor:' "$spec"; then
    sed -i -E 's/^Vendor:.*/Vendor: AAX/' "$spec"
else
    sed -i '/^Release:/a Vendor: AAX' "$spec"
fi
if [[ "$package" == python3.12-setuptools ]]; then
    cp /aax/setuptools-unicode.patch /build/rpmbuild/SOURCES/aax-setuptools-unicode.patch
    cp /aax/setuptools_regression.py /build/rpmbuild/SOURCES/aax-setuptools-regression.py
    sed -i '/^BuildArch:/i Patch9999: aax-setuptools-unicode.patch\nSource9999: aax-setuptools-regression.py\n' "$spec"
    sed -i "/^%check/a PYTHONPATH=\$PWD %{__python3} %{SOURCE9999}\n" "$spec"
fi
case "$package" in
    git-lfs|podman|skopeo)
        # Go's trimmed source paths do not populate RPM's debugsource file list.
        # Keep debuginfo and the corresponding SRPM, but omit the empty subpackage.
        sed -i '/^Name:/i %undefine _debugsource_packages' "$spec"
        cp /aax/go-vendor.sh /build/rpmbuild/SOURCES/aax-go-vendor.sh
        cp /aax/go-dependencies.json /build/rpmbuild/SOURCES/aax-go-dependencies.json
        touch /build/rpmbuild/SOURCES/aax-go-vendor.tar.gz
        sed -i '/^Name:/i Source9997: aax-go-vendor.tar.gz\nSource9998: aax-go-dependencies.json\nSource9999: aax-go-vendor.sh\n' "$spec"
        sed -i '/^%build/i bash %{SOURCE9999} %{SOURCE9998} %{SOURCE9997}\n' "$spec"
        sed -i 's/GO111MODULE=off/GO111MODULE=on/g' "$spec"
        ;;
esac
printf '%s\n' "$package" > /build/package
cp /aax/sources.json /build/output/sources.json
rpm -qp --queryformat '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE}\n' \
    /build/source.src.rpm > /build/output/original-source.txt
