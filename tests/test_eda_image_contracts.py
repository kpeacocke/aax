"""Verify the immutable runtime inputs and launcher commands for EDA."""

from pathlib import Path
from itertools import count
import json
import os
import re
import runpy
import subprocess
from types import SimpleNamespace

import pytest
import yaml


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


def test_eda_user_site_receives_fixed_msgpack() -> None:
    dockerfile = (ROOT / "images/runtime-security/EDA.Dockerfile").read_text()
    user_site = dockerfile.split("RUN PYTHONUSERBASE=/app/.local", 1)[1]
    assert "--user --upgrade" in user_site
    assert "msgpack==1.2.3" in user_site
    assert "certifi==2026.10.23" in user_site
    assert 'msgpack.__version__ == "1.2.3"' in user_site
    assert "msgpack.unpackb(msgpack.packb" in user_site
    assert "PYTHONUSERBASE=/app/.local /usr/bin/python3.12 -m pip check" in user_site


def test_eda_entrypoint_dispatches_both_workers_and_asgi() -> None:
    entrypoint = (ROOT / "images/eda-server/entrypoint.sh").read_text()

    assert "dispatcherd --worker-class DefaultWorker" in entrypoint
    assert "dispatcherd --worker-class ActivationWorker" in entrypoint
    assert "daphne -b 0.0.0.0 -p 8000 aap_eda.asgi:application" in entrypoint


def test_fresh_eda_volumes_are_writable_without_runtime_privileges() -> None:
    dockerfile = (ROOT / "images/eda-server/Dockerfile").read_text()
    assert "chown 1001:0 /home/eda/projects /var/log/eda" in dockerfile
    assert dockerfile.index("USER 0") < dockerfile.index("chown 1001:0") < dockerfile.index("USER 1001")


@pytest.mark.parametrize("occurrences", [0, 1, 2])
def test_pip_index_fixture_preserves_provenance_assertions(tmp_path: Path, occurrences: int) -> None:
    module = runpy.run_path(str(ROOT / "images/ee-base/pip-security/update-index-fixture.py"))
    path = tmp_path / "test_req.py"
    path.write_text(module["ORIGINAL"] * occurrences)
    if occurrences == 1:
        module["patch"](path)
        assert '"packaging==26.3"' in path.read_text()
        assert "resolver.ignore_installed = True" in path.read_text()
        assert "assert req.download_info.archive_info" in path.read_text()
        with pytest.raises(ValueError, match="Unexpected pip"):
            module["patch"](path)
    else:
        with pytest.raises(ValueError, match="Unexpected pip"):
            module["patch"](path)


def test_image_contracts_run_in_every_policy_command() -> None:
    for path in (".github/workflows/ci.yml", ".github/workflows/release.yml", "Makefile"):
        assert "tests/test_eda_image_contracts.py" in (ROOT / path).read_text()


def test_acceptance_rulebooks_keep_debug_alive_and_isolate_awx_action() -> None:
    directory = ROOT / "extensions/eda/rulebooks"
    debug = yaml.safe_load((directory / "aax-debug.yml").read_text())[0]
    action = yaml.safe_load((directory / "aax-awx-readiness.yml").read_text())[0]
    assert debug["sources"] == [{"ansible.eda.tick": {"delay": 5}}]
    assert "debug" in debug["rules"][0]["action"]
    assert "run_job_template" not in debug["rules"][0]["action"]
    assert {"ansible.eda.range": {"limit": 1}} in action["sources"]
    assert action["rules"][0]["condition"] == "event.i == 0"
    job = action["rules"][0]["action"]["run_job_template"]
    assert job["name"] == "RustberryPi - Readiness check"
    assert "aax_eda_acceptance_marker" in job["job_args"]["extra_vars"]


def test_acceptance_runner_rejects_external_credential_targets() -> None:
    module = runpy.run_path(str(ROOT / "scripts/test-eda-activation.py"))
    api = module["API"]("https://eda.example/api/eda/v1/", authorization="Basic test")
    with pytest.raises(ValueError, match="outside"):
        api.request("GET", "https://other.example/projects/")
    handler = module["APIRedirectHandler"](api.base_url)
    with pytest.raises(ValueError, match="outside"):
        handler.redirect_request(None, None, 302, "", {}, "https://other.example/")
    with pytest.raises(ValueError, match="loopback"):
        with module["authentication"]("admin", "https://other.example/api/eda/v1/"):
            pytest.fail("A privileged controller session must never leave loopback")


@pytest.mark.parametrize("state", [{"status": "failed"}, {"import_state": "failed"}])
def test_acceptance_poll_fails_explicitly(state: dict) -> None:
    module = runpy.run_path(str(ROOT / "scripts/test-eda-activation.py"))
    with pytest.raises(RuntimeError, match="failed"):
        module["poll"](lambda: state, lambda _: False, 1, "test")


@pytest.mark.parametrize("extra_args", [None, '@json {"network_mode":"host"}'])
def test_activation_podman_arguments_render_without_literal_quotes(extra_args: str | None) -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    value = compose["services"]["eda-activation-worker"]["environment"]["EDA_PODMAN_EXTRA_ARGS"]
    environment = dict(os.environ)
    environment.pop("EDA_PODMAN_EXTRA_ARGS", None)
    if extra_args is not None:
        environment["EDA_PODMAN_EXTRA_ARGS"] = extra_args
    result = subprocess.run(
        ["docker", "compose", "--env-file", "/dev/null", "-f", "-", "config", "--format", "json"],
        input=yaml.safe_dump({"services": {"activation": {
            "image": "test:local", "environment": {"EDA_PODMAN_EXTRA_ARGS": value},
        }}}),
        env=environment, capture_output=True, text=True, check=True, timeout=30,
    )
    rendered = json.loads(result.stdout)["services"]["activation"]["environment"]["EDA_PODMAN_EXTRA_ARGS"]
    assert rendered == (extra_args if extra_args is not None else "@json {}")


def test_acceptance_check_requires_fresh_marker_and_git_identity() -> None:
    module = runpy.run_path(str(ROOT / "scripts/test-eda-activation.py"))
    activation = {
        "status": "running", "is_enabled": True, "git_hash": "abc",
        "instances": [{"id": 8, "status": "running", "git_hash": "abc"}],
    }

    class Client:
        log_reads = 0

        def request(self, method, path):
            assert method == "GET" and path == "activations/3/"
            return activation

        def results(self, path):
            assert path == "activation-instances/8/logs/"
            self.log_reads += 1
            if self.log_reads == 1:
                return [{"id": 10, "log": "test-event"}]
            return [{"id": 10, "log": "test-event"}, {"id": 11, "log": "test-event"}]

    state = {"activation_id": 3, "git_hash": "abc", "marker": "test-event", "last_log_id": 10}
    result = module["check"](Client(), state, 1)
    assert result["last_log_id"] == 11
    assert result["instance_id"] == 8
    activation["git_hash"] = "changed"
    with pytest.raises(RuntimeError, match="Git revision"):
        module["check"](Client(), state, 1)


@pytest.mark.parametrize("replacement,race", [(False, False), (True, False), (True, True)])
def test_acceptance_check_rejects_stale_logs_and_follows_replacement(
    monkeypatch, replacement: bool, race: bool,
) -> None:
    module = runpy.run_path(str(ROOT / "scripts/test-eda-activation.py"))
    monkeypatch.setitem(
        module["check"].__globals__, "time",
        SimpleNamespace(monotonic=count().__next__, sleep=lambda _: None),
    )
    state = {"activation_id": 3, "git_hash": "abc", "marker": "test-event", "last_log_id": 10}

    class Client:
        reads = 0
        log_reads = 0

        def request(self, method, path):
            self.reads += 1
            instance_id = 9 if replacement and self.reads >= 3 else 8
            return {
                "status": "running", "is_enabled": True, "git_hash": "abc",
                "instances": [{"id": instance_id, "status": "running", "git_hash": "abc"}],
            }

        def results(self, path):
            # ID 11 persisted before this check, but after the previous successful check.
            self.log_reads += 1
            log_id = 13 if path == "activation-instances/9/logs/" else 11
            if race and self.log_reads > 1 and path == "activation-instances/8/logs/":
                log_id = 12
            return [{"id": log_id, "log": "test-event"}]

    if replacement:
        result = module["check"](Client(), state, 5)
        assert result["instance_id"] == 9
        assert result["last_log_id"] == 13
        assert result["log_watermark"] == 11
    else:
        with pytest.raises(TimeoutError, match="fresh"):
            module["check"](Client(), state, 5)


@pytest.mark.parametrize("instance_field,value", [("status", "starting"), ("git_hash", "changed")])
def test_acceptance_check_revalidates_instance_metadata(monkeypatch, instance_field: str, value: str) -> None:
    module = runpy.run_path(str(ROOT / "scripts/test-eda-activation.py"))
    monkeypatch.setitem(
        module["check"].__globals__, "time",
        SimpleNamespace(monotonic=count().__next__, sleep=lambda _: None),
    )
    instance = {"id": 8, "status": "running", "git_hash": "abc", instance_field: value}

    class Client:
        log_reads = 0

        def request(self, method, path):
            return {"status": "running", "is_enabled": True, "git_hash": "abc", "instances": [instance]}

        def results(self, path):
            self.log_reads += 1
            return [{"id": 10 + self.log_reads, "log": "test-event"}]

    state = {"activation_id": 3, "git_hash": "abc", "marker": "test-event", "last_log_id": 10}
    error = RuntimeError if instance_field == "git_hash" else TimeoutError
    with pytest.raises(error):
        module["check"](Client(), state, 5)


def test_acceptance_check_waits_for_starting_instance_identity() -> None:
    module = runpy.run_path(str(ROOT / "scripts/test-eda-activation.py"))

    class Client:
        reads = 0

        def request(self, method, path):
            self.reads += 1
            running = self.reads > 1
            return {
                "status": "running" if running else "starting", "is_enabled": True,
                "git_hash": "abc" if running else None,
                "instances": [{"id": 8, "status": "running", "git_hash": "abc"}] if running else [],
            }

        def results(self, path):
            return [{"id": 11, "log": "test-event"}]

    state = {"activation_id": 3, "git_hash": "abc", "marker": "test-event", "last_log_id": 10}
    assert module["check"](Client(), state, 1)["last_log_id"] == 11


@pytest.mark.parametrize("occurrences", [0, 1, 2])
def test_dab_openapi_upgrade_requires_exact_constraint(tmp_path: Path, occurrences: int) -> None:
    patch = runpy.run_path(str(ROOT / "images/dab-security/patch-openapi-referencing.py"))["patch"]
    source = tmp_path / "requirements.in"
    old = "referencing<0.37.0  # consistent with pin from jsonschema-path, via openapi-spec-validator"
    original = "drf-spectacular<1.0\n" + (old + "\n") * occurrences
    source.write_text(original)
    if occurrences == 1:
        patch(source)
        assert "referencing>=0.37.0,<0.38.0" in source.read_text()
        with pytest.raises(ValueError, match="Unexpected DAB"):
            patch(source)
    else:
        with pytest.raises(ValueError, match="Unexpected DAB"):
            patch(source)
        assert source.read_text() == original
