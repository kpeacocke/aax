import importlib.metadata
import importlib.util

import pytest

from pip._internal.metadata import select_backend


@pytest.fixture(autouse=True)
def clear_backend_cache():
    select_backend.cache_clear()
    yield
    select_backend.cache_clear()


def test_default_backend(monkeypatch):
    monkeypatch.delenv("_PIP_USE_IMPORTLIB_METADATA", raising=False)
    assert select_backend().NAME == "importlib"
    assert importlib.util.find_spec("pip._vendor.pkg_resources") is None
    assert importlib.util.find_spec("pip._internal.metadata.pkg_resources") is None


@pytest.mark.parametrize("value", ["false", "0", "no"])
def test_unsupported_backend_is_explicit(monkeypatch, value):
    monkeypatch.setenv("_PIP_USE_IMPORTLIB_METADATA", value)
    with pytest.raises(RuntimeError, match="does not ship"):
        select_backend()


def test_distributor_override_is_explicit(monkeypatch):
    monkeypatch.delenv("_PIP_USE_IMPORTLIB_METADATA", raising=False)
    monkeypatch.setattr(importlib.metadata, "_PIP_USE_IMPORTLIB_METADATA", False, raising=False)
    with pytest.raises(RuntimeError, match="distributor override"):
        select_backend()


def test_explicit_importlib_backend(monkeypatch):
    monkeypatch.setenv("_PIP_USE_IMPORTLIB_METADATA", "true")
    assert select_backend().NAME == "importlib"
