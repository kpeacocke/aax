"""Verify the immutable runtime inputs and launcher commands for EDA."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_decision_environment_pins_rulebook_and_collection() -> None:
    dockerfile = (ROOT / "images/eda-decision-environment/Dockerfile").read_text()

    assert re.search(r"^ARG BASE_IMAGE=.*@sha256:[0-9a-f]{64}$", dockerfile, re.MULTILINE)
    assert "ansible.eda" in dockerfile
    assert r"2\.13\.0" in dockerfile


def test_podman_backend_uses_persistent_vfs_storage() -> None:
    dockerfile = (ROOT / "images/eda-podman/Dockerfile").read_text()

    assert re.search(r"^ARG BASE_IMAGE=.*@sha256:[0-9a-f]{64}$", dockerfile, re.MULTILINE)
    assert 'driver = "vfs"' in dockerfile
    assert 'graphroot = "/var/lib/containers/storage"' in dockerfile
    assert 'VOLUME ["/var/lib/containers/storage"]' in dockerfile
    assert 'tcp://0.0.0.0:8888' in dockerfile


def test_eda_entrypoint_dispatches_both_workers_and_asgi() -> None:
    entrypoint = (ROOT / "images/eda-server/entrypoint.sh").read_text()

    assert "dispatcherd --worker-class DefaultWorker" in entrypoint
    assert "dispatcherd --worker-class ActivationWorker" in entrypoint
    assert "daphne -b 0.0.0.0 -p 8000 aap_eda.asgi:application" in entrypoint
