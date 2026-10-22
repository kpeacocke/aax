"""Execute publication and vulnerability-gate scripts without registry writes."""

import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/publish-devel.yml").read_text())
STEPS = WORKFLOW["jobs"]["build-and-publish"]["steps"]
IMAGES = ["awx", "awx-ee", "receptor", "ansible-rulebook", "galaxy-ng", "gateway", "eda-controller"]


def script(name: str) -> str:
    return next(step["run"] for step in STEPS if step["name"] == name)


def test_scheduled_builds_and_retries_have_distinct_tags() -> None:
    template = WORKFLOW["env"]["IMAGE_TAG"]

    def tag(run_id: str, attempt: str) -> str:
        return (
            template.replace("${{ github.sha }}", "same-commit")
            .replace("${{ github.run_id }}", run_id)
            .replace("${{ github.run_attempt }}", attempt)
        )

    assert len({tag("10", "1"), tag("11", "1"), tag("11", "2")}) == 3


@pytest.mark.parametrize("mutable", [True, False])
@pytest.mark.parametrize("fail_push", [True, False])
def test_publisher_never_skips_fresh_images(
    tmp_path: Path, mutable: bool, fail_push: bool
) -> None:
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\n'
        'printf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
        'if [[ "$1" == push && "$FAIL_PUSH" == true ]]; then exit 1; fi\n'
        'if [[ "$1" == buildx ]]; then printf "{}\\n"; fi\n'
    )
    docker.chmod(0o755)
    (tmp_path / "bundle-reports").mkdir()
    log = tmp_path / "docker.log"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "FAIL_PUSH": str(fail_push).lower(),
        "PUSH_MUTABLE": str(mutable).lower(),
        "IMAGE_OWNER": "TestOwner",
        "REGISTRY": "ghcr.io",
        "IMAGE_TAG": "devel-commit-101-1",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }
    result = subprocess.run(
        ["bash", "-c", script("Tag and push bundle")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    commands = log.read_text().splitlines()
    pushes = [command for command in commands if command.startswith("push ")]
    if fail_push:
        assert result.returncode != 0
        assert len(pushes) == 1
        assert all(not command.endswith(":devel") for command in pushes)
        return
    assert result.returncode == 0, result.stderr
    assert len(pushes) == (16 if mutable else 8)
    assert all(command.endswith(":devel-commit-101-1") for command in pushes[:8])
    assert len({command for command in pushes[:8]}) == 8
    assert len(list((tmp_path / "bundle-reports").glob("*-manifest.json"))) == 8
    if mutable:
        assert all(command.endswith(":devel") for command in pushes[8:])


@pytest.mark.parametrize(
    ("severity", "fixed", "blocked"),
    [("CRITICAL", "2.0", True), ("HIGH", "2.0", True),
     ("CRITICAL", "", False), ("MEDIUM", "2.0", False)],
)
def test_gate_measures_fixed_version_and_severity(
    tmp_path: Path, severity: str, fixed: str, blocked: bool
) -> None:
    reports = tmp_path / "bundle-reports"
    reports.mkdir()
    (tmp_path / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    for image in IMAGES:
        (reports / f"{image}.json").write_text(json.dumps({"SchemaVersion": 2, "Results": []}))
    finding = {"VulnerabilityID": "TEST-CVE", "Severity": severity, "FixedVersion": fixed}
    (reports / "awx.json").write_text(
        json.dumps({"SchemaVersion": 2, "Results": [{"Vulnerabilities": [finding]}]})
    )
    result = subprocess.run(
        ["bash", "-c", script("Gate on fixable high and critical bundle vulnerabilities")],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode != 0) == blocked, result.stderr


def test_bundle_scan_precedes_publication() -> None:
    names = [step.get("name", "") for step in STEPS]
    assert names.index("Scan exact bundle images") < names.index(
        "Gate on fixable high and critical bundle vulnerabilities"
    ) < names.index("Tag and push bundle")
    scan = script("Scan exact bundle images")
    for image in IMAGES:
        assert image in scan
    assert "set -euo pipefail" in scan


@pytest.mark.parametrize("contents", ["{}", "[]", "null", "not json"])
def test_invalid_reports_cannot_pass_the_gate(tmp_path: Path, contents: str) -> None:
    report = tmp_path / "invalid.json"
    report.write_text(contents)
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/check-vulnerability-reports.sh"), str(report)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


def test_main_channel_promotes_only_scanned_candidate_digests() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish-images.yml").read_text())
    for job in workflow["jobs"].values():
        steps = job["steps"]
        names = [step.get("name", "") for step in steps]
        assert names.index("Scan candidate on both architectures before promotion") < names.index(
            "Promote scanned candidate"
        )
        build = next(step for step in steps if step.get("id") == "build")
        assert ":build-${{ github.run_id }}-${{ github.run_attempt }}" in build["with"]["tags"]
        scan = next(step for step in steps if step.get("name", "").startswith("Scan candidate"))
        assert "for arch in amd64 arm64" in scan["run"]
        assert "@${{ steps.build.outputs.digest }}" in scan["env"]["IMAGE"]
        assert "bash scripts/check-vulnerability-reports.sh" in scan["run"]
    base = workflow["jobs"]["build-and-push"]["steps"]
    base_arg = next(step for step in base if step.get("id") == "base")
    assert "aax-ee-base@$BASE_DIGEST" in base_arg["run"]
