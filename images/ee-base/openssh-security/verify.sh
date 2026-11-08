#!/bin/sh
set -eu
directory="$(find /source -mindepth 1 -maxdepth 1 -type d -name 'openssh-*')"
test -n "$directory"
cd "$directory"
export QUILT_PATCH_OPTS=--fuzz=0
/usr/bin/python3 /patches/test_rekey.py > /output/provenance/rekey-runtime.log 2>&1

build_asan() {
    make -C debian/build-deb clean
    make -C debian/build-deb -j2 ssh \
        CFLAGS="$(dpkg-buildflags --get CFLAGS) -O1 -g -fsanitize=address -fno-omit-frame-pointer" \
        LDFLAGS="-L. -Lopenbsd-compat $(dpkg-buildflags --get LDFLAGS) -fsanitize=address"
}

quilt pop
build_asan
if (cd debian/build-deb && /usr/bin/python3 /patches/test_rekey.py --asan) \
    > /output/provenance/rekey-unpatched-asan.log 2>&1; then
    echo 'Unpatched client unexpectedly passed the lifetime regression' >&2
    exit 1
fi
cat /output/provenance/rekey-unpatched-asan.log
grep -F 'heap-use-after-free' /output/provenance/rekey-unpatched-asan.log
quilt push
build_asan
(cd debian/build-deb && /usr/bin/python3 /patches/test_rekey.py --asan) \
    > /output/provenance/rekey-patched-asan.log 2>&1
cat /output/provenance/rekey-runtime.log /output/provenance/rekey-patched-asan.log
