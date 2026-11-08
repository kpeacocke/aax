#!/bin/sh
set -eu
test "$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')" = 3.14
mkdir -p /source /output/usr/local/share/aax/python-security
cd /source
curl --fail --location --retry 3 --connect-timeout 30 --max-time 600 \
    -o python.tar.xz "https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz"
echo "$PYTHON_SHA256  python.tar.xz" | sha256sum --check -
tar -xf python.tar.xz --strip-components=1
while read -r checksum filename; do
    revision="${filename%.patch}"
    curl --fail --location --retry 3 --connect-timeout 30 --max-time 120 \
        -o "$filename" "https://github.com/python/cpython/commit/$revision.patch"
    echo "$checksum  $filename" | sha256sum --check -
    git apply --include=Lib/poplib.py --include=Lib/http/client.py "$filename"
    cp "$filename" /output/usr/local/share/aax/python-security/
done < /patches/patches.sha256
git apply /patches/socket-nul-3.14.patch
extension="$(python -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')"
# Use the matching interpreter's headers and build flags, preserving its ABI.
# shellcheck disable=SC2046
gcc -shared -fPIC $(python3-config --cflags) \
    -I/source/Include -I/source/Include/internal -I/source/Modules \
    Modules/socketmodule.c $(python3-config --ldflags) -o "_socket$extension"
library=/output/usr/local/lib/python3.14
mkdir -p "$library/lib-dynload" "$library/http"
cp "_socket$extension" "$library/lib-dynload/"
cp Lib/poplib.py "$library/"
cp Lib/http/client.py "$library/http/"
cp /patches/socket-nul-3.14.patch /patches/patches.sha256 \
    /output/usr/local/share/aax/python-security/
python -c 'import json, os, platform, sysconfig; print(json.dumps({
    "version": os.environ["PYTHON_VERSION"], "source_sha256": os.environ["PYTHON_SHA256"],
    "soabi": sysconfig.get_config_var("SOABI"), "architecture": platform.machine(),
}))' > /output/usr/local/share/aax/python-security/provenance.json
