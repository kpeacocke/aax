#!/bin/sh
set -eu
git init
git remote add origin https://github.com/pypa/pip.git
git fetch --depth 1 origin b3b696fe2122f2339d782517559bfade2cb6b879
git checkout --detach FETCH_HEAD
cp /patches/requirements-vendor.txt src/pip/_vendor/vendor.txt
git apply /patches/importlib-only.patch
rm tools/vendoring/patches/pkg_resources.patch src/pip/_internal/metadata/pkg_resources.py
sed -i 's/__version__ = "26.2.2"/__version__ = "26.2.2+aax.2"/' src/pip/__init__.py
grep -q '__version__ = "26.2.2+aax.2"' src/pip/__init__.py
python -m pip install --no-cache-dir pip==26.2.2 'vendoring~=1.4.0' build
vendoring sync -v
python -m pip install --no-cache-dir --group test
PYTHONPATH=src python -W error -c 'from pip._vendor import msgpack, urllib3; from pip._internal.metadata import select_backend; assert select_backend().NAME == "importlib"'
cp /patches/test_importlib_only.py tests/unit/test_aax_importlib_only.py
PYTHONPATH=src python -m pytest -q tests/unit/test_aax_importlib_only.py
PYTHONPATH=src python -m pytest -q tests/unit/test_packaging.py tests/unit/test_req.py
python -m build --wheel --outdir /wheels
