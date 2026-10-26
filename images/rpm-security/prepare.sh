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
        # autosetup's synthetic Git commit is not upstream version provenance.
        # Disable its pseudo-version; the RPM and tool's own version identify source.
        # shellcheck disable=SC2016
        sed -i '/^%build/a export GOFLAGS="${GOFLAGS:-} -buildvcs=false"\nexport GOWORK=off' "$spec"
        sed -i 's/GO111MODULE=off/GO111MODULE=on/g' "$spec"
        ;;
esac
if [[ "$package" == podman ]]; then
    # Retain the signed distribution recipe, replacing Source0 with real upstream
    # source. The replacement and its exact revision remain in the rebuilt SRPM.
    version="$(jq -er '.podman.upstream.version' /aax/sources.json)"
    revision="$(jq -er '.podman.upstream.revision' /aax/sources.json)"
    upstream_url="$(jq -er '.podman.upstream.url' /aax/sources.json)"
    upstream_checksum="$(jq -er '.podman.upstream.sha256' /aax/sources.json)"
    source_name="podman-$version-${revision:0:7}.tar.gz"
    curl --fail --location --retry 3 --connect-timeout 30 --max-time 1800 \
        --output "/build/rpmbuild/SOURCES/$source_name" "$upstream_url"
    echo "$upstream_checksum  /build/rpmbuild/SOURCES/$source_name" | sha256sum --check -
    sed -i -E "s/^Version:.*/Version: $version/; s/^%global commit0 .*/%global commit0 $revision/" "$spec"
    cp /aax/podman-runtime-spec.patch /build/rpmbuild/SOURCES/aax-podman-runtime-spec.patch
    sed -i '/^Name:/i Patch9996: aax-podman-runtime-spec.patch' "$spec"
    # Backport upstream 56e555bfc213 and 8c4edb612187 to the v5 API.
    cp /aax/podman-moby-api.patch /build/rpmbuild/SOURCES/aax-podman-moby-api.patch
    sed -i '/^Name:/i Patch9995: aax-podman-moby-api.patch' "$spec"
    touch /build/rpmbuild/SOURCES/aax-dnsname-vendor.tar.gz
    sed -i '/^Name:/i Source9994: aax-dnsname-vendor.tar.gz' "$spec"
    sed -i '/^%build/i pushd dnsname-%{commit_dnsname}\nbash %{SOURCE9999} %{SOURCE9998} %{SOURCE9994}\npopd\n' "$spec"
    # The EL9 recipe's GOPATH-era import path omits Podman's /v5 module suffix.
    sed -i 's|%{import_path}/cmd/|./cmd/|g' "$spec"
    sed -i 's|%{import_path}/libpod/|%{import_path}/v5/libpod/|g' "$spec"
    # Go's content-addressed build cache validates source/toolchain inputs for
    # every shipped target; forcing all dependencies to rebuild defeats it.
    sed -i 's/ -a -v / -v /g' "$spec"
fi
if [[ "$package" == skopeo ]]; then
    # Modern Go/FIPS uses standard crypto APIs, not the removed ecdsa.HashSign API.
    macro="$(rpm --eval '%{macrobody:gobuild}' | sed '/^$/d')"
    [[ "$macro" == *"go build "* ]] || {
        echo "Cannot adapt skopeo: missing Go RPM build macro" >&2
        exit 1
    }
    macro="${macro//\\/\\\\}"
    temporary="${spec}.aax"
    {
        printf '%%define gobuild(o:) \\\n%s\n\n' "${macro// libtrust_openssl/}"
        sed 's/ libtrust_openssl//g' "$spec"
    } > "$temporary"
    mv "$temporary" "$spec"
fi
printf '%s\n' "$package" > /build/package
cp /aax/sources.json /build/output/sources.json
rpm -qp --queryformat '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE}\n' \
    /build/source.src.rpm > /build/output/original-source.txt
