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


def test_decision_environment_receives_runtime_security_patches() -> None:
    dockerfile = (ROOT / "images/eda-decision-environment/Security.Dockerfile").read_text()
    workflow = (ROOT / ".github/workflows/publish-devel.yml").read_text()
    patch_script = (ROOT / "scripts/patch-bundle-image.sh").read_text()

    assert "ARG PIP_IMAGE=aax/pip-security:devel" in dockerfile
    assert "ARG DROOLS_IMAGE=ansible-rulebook:patched" in dockerfile
    assert "dnf -y remove tracker-miners webkit2gtk3-jsc" in dockerfile
    assert "python3.12 -m pip install --no-cache-dir --user --upgrade" in dockerfile
    assert "requirements-decision-environment.txt" in dockerfile
    assert "python3.12 -m pip check" in dockerfile
    assert "python3.12 -m pip cache purge" in dockerfile
    patch = workflow.index("- name: Apply maintained runtime security patches")
    execution = workflow.index("- name: Verify nested Podman execution and outbound HTTPS")
    assert patch < execution
    assert "docker build -f images/eda-decision-environment/Security.Dockerfile" in patch_script
    assert 'docker tag "$name:patched" "$name:devel"' in patch_script
    assert "--rulebook /dev/stdin --shutdown-delay 1 < tests/fixtures/eda-smoke.yml" in workflow
    assert "grep -Fq AAX_DECISION_SECURITY_SMOKE_PASSED bundle-reports/eda-rulebook-smoke.log" in workflow


def test_eda_entrypoint_dispatches_both_workers_and_asgi() -> None:
    entrypoint = (ROOT / "images/eda-server/entrypoint.sh").read_text()

    assert "dispatcherd --worker-class DefaultWorker" in entrypoint
    assert "dispatcherd --worker-class ActivationWorker" in entrypoint
    assert "daphne -b 0.0.0.0 -p 8000 aap_eda.asgi:application" in entrypoint


def test_image_contracts_run_in_every_policy_command() -> None:
    for path in (".github/workflows/ci.yml", ".github/workflows/release.yml", "Makefile"):
        assert "tests/test_eda_image_contracts.py" in (ROOT / path).read_text()
