#!/bin/sh
set -eu
runtime_version="$(python -c 'import platform; print(platform.python_version())')"
test "$runtime_version" = "$PYTHON_VERSION"
python_minor="${runtime_version%.*}"
mkdir -p /source /output/usr/local/share/aax/python-security

write_provenance() {
    python -c 'import json, os, platform, sysconfig; print(json.dumps({
        "version": os.environ["PYTHON_VERSION"], "source_sha256": os.environ["PYTHON_SHA256"],
        "soabi": sysconfig.get_config_var("SOABI"), "architecture": platform.machine(),
    }))' > /output/usr/local/share/aax/python-security/provenance.json
}

apply_python_patch() {
    patch_file=$1
    if git apply --include=Lib/poplib.py --include=Lib/http/client.py --check "$patch_file" >/dev/null 2>&1; then
        git apply --include=Lib/poplib.py --include=Lib/http/client.py "$patch_file"
    elif git apply --include=Lib/poplib.py --include=Lib/http/client.py --reverse --check "$patch_file" >/dev/null 2>&1; then
        printf '%s is already present in CPython %s\n' "$patch_file" "$PYTHON_VERSION"
    else
        printf 'Patch does not apply to CPython %s: %s\n' "$PYTHON_VERSION" "$patch_file" >&2
        exit 1
    fi
}

case "$python_minor" in
    3.14|3.15) ;;
    *)
        echo "Unsupported Python version for the security backports: $runtime_version" >&2
        exit 1
        ;;
esac

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
    apply_python_patch "$filename"
    cp "$filename" /output/usr/local/share/aax/python-security/
done < /patches/patches.sha256
if git apply --check /patches/socket-nul.patch >/dev/null 2>&1; then
    git apply /patches/socket-nul.patch
elif git apply --reverse --check /patches/socket-nul.patch >/dev/null 2>&1; then
    printf 'socket null-byte fix is already present in CPython %s\n' "$PYTHON_VERSION"
else
    echo "Socket null-byte patch does not apply to CPython $PYTHON_VERSION" >&2
    exit 1
fi
extension="$(python -c 'import sysconfig; print(sysconfig.get_config_var("EXT_SUFFIX"))')"
# Use the matching interpreter's headers and build flags, preserving its ABI.
# shellcheck disable=SC2046
gcc -shared -fPIC $(python3-config --cflags) \
    -I/source/Include -I/source/Include/internal -I/source/Modules \
    Modules/socketmodule.c $(python3-config --ldflags) -o "_socket$extension"
library="/output$(python -c 'import sysconfig; print(sysconfig.get_path("stdlib"))')"
mkdir -p "$library/lib-dynload" "$library/http"
cp "_socket$extension" "$library/lib-dynload/"
cp Lib/poplib.py "$library/"
cp Lib/http/client.py "$library/http/"
cp /patches/socket-nul.patch /patches/patches.sha256 \
    /output/usr/local/share/aax/python-security/
write_provenance
