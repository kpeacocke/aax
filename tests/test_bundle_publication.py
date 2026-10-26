"""Execute publication and vulnerability-gate scripts without registry writes."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import runpy
import zipfile

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/publish-devel.yml").read_text())
STEPS = WORKFLOW["jobs"]["build-and-publish"]["steps"]
IMAGES = ["awx", "awx-ee", "receptor", "ansible-rulebook", "galaxy-ng", "gateway", "eda-controller"]


@pytest.mark.parametrize(
    ("options", "valid"),
    [("required=True, allow_null=False", True),
     ("required=False, allow_null=False", False),
     ("required=True, allow_null=True", False),
     ("allow_null=False", False),
     ("required=True, allow_null=False, default=None", False)],
)
def test_upstream_oauth_fix_requires_explicit_safe_field(
    tmp_path: Path, options: str, valid: bool
) -> None:
    verify = runpy.run_path(str(ROOT / "images/dab-security/apply-oauth-patch.py"))[
        "verify_upstream_fix"
    ]
    source = tmp_path / "application.py"
    source.write_text(
        "class OAuth2ApplicationSerializer:\n"
        f"    organization = serializers.PrimaryKeyRelatedField({options})\n"
    )
    if valid:
        verify(source)
    else:
        with pytest.raises(ValueError):
            verify(source)


def script(name: str) -> str:
    return next(step["run"] for step in STEPS if step["name"] == name)


@pytest.mark.parametrize("incomplete", [False, True])
def test_sarif_has_unique_image_scanner_identities(tmp_path: Path, incomplete: bool) -> None:
    reports = tmp_path / "bundle-reports"
    reports.mkdir()
    original = {
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "scanner"}},
            "results": [{"ruleId": "TEST-CVE", "message": {"text": "preserve me"}}],
        }],
    }
    expected = set()
    for name in IMAGES:
        for scanner in ("trivy", "grype"):
            if incomplete and scanner == "grype":
                continue
            filename = f"{name}-grype.sarif" if scanner == "grype" else f"{name}.sarif"
            (reports / filename).write_text(json.dumps(original))
            expected.add(f"devel-bundle/{scanner}/{name}/")
    result = subprocess.run(
        ["bash", "-c", script("Give security reports distinct analysis identities")],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    identities = []
    for report in (tmp_path / "bundle-sarif").glob("*.sarif"):
        data = json.loads(report.read_text())
        assert data["runs"][0]["results"] == original["runs"][0]["results"]
        identities.append(data["runs"][0]["automationDetails"]["id"])
    assert len(identities) == len(set(identities))
    assert set(identities) == expected
    upload = next(step for step in STEPS if step["name"] == "Upload bundle security findings")
    assert upload["with"] == {"sarif_file": "bundle-sarif"}


@pytest.mark.parametrize("installed,removal_fails", [(False, False), (True, False), (True, True)])
def test_system_setuptools_removal_respects_rpm_dependencies(
    tmp_path: Path, installed: bool, removal_fails: bool
) -> None:
    rpm = tmp_path / "rpm"
    rpm.write_text(
        '#!/bin/sh\n'
        'echo "$*" >> "$RPM_LOG"\n'
        'if [ "$1" = -qa ]; then printf "%s\\n" "$PACKAGES"; exit 0; fi\n'
        'if [ "$*" != "--erase python3.12-setuptools" ]; then exit 2; fi\n'
        'if [ "$REMOVAL_FAILS" = true ]; then echo "Failed dependencies" >&2; exit 1; fi\n'
    )
    rpm.chmod(0o755)
    log = tmp_path / "rpm.log"
    result = subprocess.run(
        ["sh", str(ROOT / "images/runtime-security/remove-build-setuptools.sh")],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "RPM_LOG": str(log), "REMOVAL_FAILS": str(removal_fails).lower(),
             "PACKAGES": "python3.12-setuptools\npython3.12-pip" if installed else "python3.12-pip"},
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode != 0) == removal_fails
    commands = log.read_text().splitlines()
    assert ("--erase python3.12-setuptools" in commands) == installed
    runtime = script("Apply maintained runtime security patches")
    assert runtime.index('docker tag "$name:rpm-patched"') < runtime.index(
        "images/runtime-security/Finalize.Dockerfile"
    ) < runtime.index("'awx-ee /usr/bin/python3.12 1000 awx-ee'")


@pytest.mark.parametrize("valid", [True, False])
def test_frozen_upstream_input_is_validated_before_checkout(tmp_path: Path, valid: bool) -> None:
    (tmp_path / "scripts").mkdir()
    checkout = tmp_path / "scripts/build-upstream.sh"
    checkout.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$AWX_BRANCH" "$AWX_EE_BRANCH" "$RECEPTOR_BRANCH" '
        '"$RULEBOOK_BRANCH" "$GALAXY_NG_BRANCH" > checked-out\n'
    )
    checkout.chmod(0o755)
    revisions = {name: str(index) * 40 for index, name in enumerate(IMAGES[:5], 1)}
    if not valid:
        revisions["awx"] = "devel"
    result = subprocess.run(
        ["bash", "-c", script("Check out upstream sources")],
        cwd=tmp_path, env={**os.environ, "UPSTREAM_REVISIONS": json.dumps(revisions)},
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode == 0) == valid, result.stderr
    if valid:
        assert (tmp_path / "checked-out").read_text().splitlines() == list(revisions.values())
    else:
        assert not (tmp_path / "checked-out").exists()


@pytest.mark.parametrize("cached_mismatch", [False, True])
def test_upstream_checkout_fetches_and_checks_exact_commits(
    tmp_path: Path, cached_mismatch: bool
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    checkout = scripts / "build-upstream.sh"
    checkout.write_text((ROOT / "scripts/build-upstream.sh").read_text())
    git = tmp_path / "git"
    git.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$GIT_LOG"\n'
        'if [ "$3" = rev-parse ]; then printf "%s\\n" "$ACTUAL_SHA"; fi\n'
    )
    git.chmod(0o755)
    revision = "a" * 40
    if cached_mismatch:
        (tmp_path / ".upstream/awx/.git").mkdir(parents=True)
    log = tmp_path / "git.log"
    result = subprocess.run(
        ["bash", str(checkout)], capture_output=True, text=True, timeout=10,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "GIT_LOG": str(log), "AWX_DAB_REF": "",
             "ACTUAL_SHA": "b" * 40 if cached_mismatch else revision,
             **{key: revision for key in ("AWX_BRANCH", "AWX_EE_BRANCH", "RECEPTOR_BRANCH",
                                         "RULEBOOK_BRANCH", "GALAXY_NG_BRANCH")}},
    )
    commands = log.read_text().splitlines()
    if cached_mismatch:
        assert result.returncode != 0
        assert "does not match requested commit" in result.stderr
        assert len(commands) == 1
    else:
        assert result.returncode == 0, result.stderr
        assert sum(f"fetch --depth 1 origin {revision}" in command for command in commands) == 5
        assert sum("checkout --detach FETCH_HEAD" in command for command in commands) == 5


@pytest.mark.parametrize("layout", ["setup.py", "pyproject.toml", "missing"])
def test_hub_patch_selection_checks_before_applying(tmp_path: Path, layout: str) -> None:
    if layout != "missing":
        (tmp_path / layout).touch()
    git = tmp_path / "git"
    git.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$GIT_LOG"\n')
    git.chmod(0o755)
    log = tmp_path / "git.log"
    result = subprocess.run(
        ["bash", str(ROOT / "images/hub-security/patch-galaxy.sh"),
         str(tmp_path), str(ROOT / "images/hub-security")],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "GIT_LOG": str(log)},
        capture_output=True, text=True, timeout=10,
    )
    if layout == "missing":
        assert result.returncode != 0
        assert "No supported Galaxy packaging" in result.stderr
        assert not log.exists()
        return
    assert result.returncode == 0, result.stderr
    patch = "galaxy.patch" if layout == "setup.py" else "galaxy-pyproject.patch"
    assert log.read_text().splitlines() == [
        f"-C {tmp_path} apply --check {ROOT / 'images/hub-security' / patch}",
        f"-C {tmp_path} apply {ROOT / 'images/hub-security' / patch}",
    ]


@pytest.mark.parametrize("version", ["2026.9.17.0.dev74+aax.1", "2026.10.9.0.dev104+aax.1"])
def test_eda_requires_exact_verified_dab_wheel(tmp_path: Path, version: str) -> None:
    pin = runpy.run_path(str(ROOT / "images/runtime-security/pin_eda_dab.py"))["pin"]
    project = tmp_path / "pyproject.toml"
    original = (
        'django-ansible-base = { version = ">=2026.10.21.1.dev2", extras = ["rbac"] }\n'
    )
    project.write_text(original)
    with pytest.raises(ValueError, match="Expected one verified"):
        pin(project, tmp_path)
    wheel_path = tmp_path / f"django_ansible_base-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as wheel:
        wheel.writestr(
            f"django_ansible_base-{version}.dist-info/METADATA",
            f"Name: django-ansible-base\nVersion: {version}\n",
        )
    pin(project, tmp_path)
    assert project.read_text() == original.replace(">=2026.10.21.1.dev2", f"=={version}")
    with pytest.raises(ValueError, match="Expected one patched"):
        pin(project, tmp_path)


def grype_report(image_id: str = "sha256:test", matches: tuple[dict, ...] = ()) -> dict:
    return {
        "descriptor": {"name": "grype", "db": {"status": {"valid": True}}},
        "source": {"type": "image", "target": {"imageID": image_id}},
        "distro": {"name": "centos"},
        "matches": list(matches),
    }


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
    (reports / "awx-grype.json").write_text(json.dumps(grype_report()))
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
    assert '"$RUNNER_TEMP/grype"' in scan
    assert 'json=bundle-reports/$name-grype.json' in scan
    assert 'sarif=bundle-reports/$name-grype.sarif' in scan
    assert "sha256sum --check -" in script("Install supplemental OS scanner")


@pytest.mark.parametrize(
    ("severity", "state", "blocked"),
    [("Critical", "fixed", True), ("High", "fixed", True),
     ("Medium", "fixed", False), ("High", "not-fixed", False)],
)
def test_supplemental_gate_measures_real_fix_state(
    tmp_path: Path, severity: str, state: str, blocked: bool
) -> None:
    report = tmp_path / "grype.json"
    report.write_text(json.dumps(grype_report(matches=({
        "vulnerability": {
            "id": "TEST-CVE", "severity": severity,
            "fix": {"state": state, "versions": ["2.0"] if state == "fixed" else []},
        },
    },))))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/check-vulnerability-reports.sh"), str(report)],
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode != 0) == blocked, result.stderr


@pytest.mark.parametrize("matching_image", [True, False])
def test_missing_os_coverage_needs_exact_image_supplement(
    tmp_path: Path, matching_image: bool
) -> None:
    trivy = tmp_path / "trivy.json"
    trivy.write_text(json.dumps({
        "SchemaVersion": 2, "Results": [],
        "Metadata": {"ImageID": "sha256:exact", "OS": {"Family": "centos-stream"}},
    }))
    grype = tmp_path / "grype.json"
    grype.write_text(json.dumps(grype_report("sha256:exact" if matching_image else "sha256:other")))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/check-vulnerability-reports.sh"), str(trivy), str(grype)],
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode == 0) == matching_image, result.stderr


def test_invalid_supplemental_database_is_not_a_clean_scan(tmp_path: Path) -> None:
    report = grype_report()
    report["descriptor"]["db"]["status"]["valid"] = False
    path = tmp_path / "grype.json"
    path.write_text(json.dumps(report))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/check-vulnerability-reports.sh"), str(path)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0


def test_runtime_security_updates_precede_exact_image_scans(tmp_path: Path) -> None:
    names = [step.get("name", "") for step in STEPS]
    assert names.index("Apply maintained runtime security patches") < names.index(
        "Scan exact bundle images"
    )
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
        'if [[ "$1" == run ]]; then printf "%040d 2026.10.21.1.dev2+aax.2\\n" 1; fi\n'
    )
    docker.chmod(0o755)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "build-rpm-security.sh").write_text(
        '#!/bin/bash\nprintf "build-source-rpms %s\\n" "$*" >> "$DOCKER_LOG"\n'
    )
    log = tmp_path / "docker.log"
    result = subprocess.run(
        ["bash", "-c", script("Apply maintained runtime security patches").replace(
            "${{ github.sha }}", "test-sha"
        )],
        cwd=tmp_path,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "DOCKER_LOG": str(log),
        },
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    commands = log.read_text().splitlines()
    assert "build-source-rpms bundle-reports/rpm-security" in commands
    for name in ("awx", "awx-ee", "galaxy-ng", "eda-controller", "ansible-rulebook", "receptor"):
        rpm_build = next(
            command for command in commands if f"-t {name}:rpm-patched " in command
        )
        assert "images/rpm-security/Runtime.Dockerfile" in rpm_build
        assert commands.index(rpm_build) > commands.index(
            "build-source-rpms bundle-reports/rpm-security"
        )
    for name in ("awx", "awx-ee", "galaxy-ng", "eda-controller"):
        build = next(command for command in commands if f"-t {name}:python-patched " in command)
        assert f"BASE_IMAGE={name}:devel" in build
        assert "RUNTIME_USER=" in build and "PYTHON=" in build
    assert any("RECEPTOR_IMAGE=receptor:devel" in command for command in commands)
    assert any("images/runtime-security/EDA.Dockerfile" in command for command in commands)
    for name in ("awx", "galaxy-ng", "eda-controller"):
        source_build = next(
            command for command in commands if f"-t aax/dab-security:{name} " in command
        )
        assert "DAB_REVISION=" + "0" * 39 + "1" in source_build
        assert "DAB_VERSION=2026.10.21.1.dev2+aax.2" in source_build
        assert any(f"DAB_IMAGE=aax/dab-security:{name}" in command for command in commands)
        evidence = json.loads((tmp_path / f"bundle-reports/{name}-dab-source.json").read_text())
        assert evidence["revision"] == "0" * 39 + "1"
    dockerfile = (ROOT / "images/runtime-security/Dockerfile").read_text()
    assert '"${PYTHON}" -m pip check' in dockerfile
    assert any(
        "BASE_IMAGE=awx:devel" in command
        and "PYTHON=/usr/bin/python3.12" in command
        and "REQUIREMENTS=requirements-awx-system.txt" in command
        for command in commands
    )


def test_java_database_has_independent_public_registry_fallback() -> None:
    scan = next(step for step in STEPS if step.get("name") == "Scan exact bundle images")
    assert "public.ecr.aws/aquasecurity/trivy-java-db:1" in scan["env"]["TRIVY_JAVA_DB_REPOSITORY"]


@pytest.mark.parametrize(
    ("installed", "version", "fail_upgrade", "success"),
    [(True, "0:2-1.x86_64", False, True),
     (False, "0:2-1.x86_64", False, False),
     (True, "0:3-1.x86_64", False, False),
     (True, "0:2-1.x86_64", True, False)],
)
def test_rpm_installer_only_upgrades_existing_packages_and_checks_result(
    tmp_path: Path, installed: bool, version: str, fail_upgrade: bool, success: bool
) -> None:
    directory = tmp_path / "rpms"
    directory.mkdir()
    for name in ("runtime", "unused-server"):
        (directory / f"{name}.rpm").touch()
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "rpm").write_text(
        '#!/bin/bash\n'
        'if [[ "$1" == --upgrade || "$1" == --verify ]]; then\n'
        '  printf "%s\\n" "$*" >> "$PACKAGE_LOG"\n'
        '  if [[ "$1" == --upgrade && "$FAIL_UPGRADE" == true ]]; then\n'
        '    echo "upgrade failed" >&2; exit 1\n'
        '  fi\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "$1" == -qp ]]; then\n'
        '  if [[ "$3" == "%{NAME}" ]]; then\n'
        '    name="${4##*/}"; printf "%s" "${name%.rpm}"\n'
        '  else printf "0:2-1.x86_64"; fi\n'
        'elif [[ "${*: -1}" != runtime || "$INSTALLED" != true ]]; then exit 1\n'
        'elif [[ "$2" == --queryformat ]]; then printf "%s" "$VERSION"\n'
        'fi\n'
    )
    for executable in binary.iterdir():
        executable.chmod(0o755)
    log = tmp_path / "rpm.log"
    result = subprocess.run(
        ["bash", str(ROOT / "images/rpm-security/install.sh"), str(directory)],
        env={
            **os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
            "PACKAGE_LOG": str(log), "INSTALLED": str(installed).lower(),
            "VERSION": version, "FAIL_UPGRADE": str(fail_upgrade).lower(),
        },
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode == 0) == success, result.stderr
    commands = log.read_text().splitlines() if log.exists() else []
    assert all("unused-server" not in command for command in commands)
    if success:
        assert commands == [
            f"--upgrade {directory}/runtime.rpm", "--verify --all --nofiles --noscripts"
        ]
    elif not installed:
        assert commands == []
        assert "No applicable AAX security RPMs" in result.stderr
    elif fail_upgrade:
        assert "upgrade failed" in result.stderr
    else:
        assert "expected 0:2-1.x86_64, found 0:3-1.x86_64" in result.stderr


@pytest.mark.parametrize(
    ("current", "list_failure", "success"),
    [("v0.59.0", False, True), ("v0.61.0", False, False),
     ("", False, True), ("v0.59.0", True, False)],
)
@pytest.mark.parametrize("preparation_failure", ["", "tidy", "download"])
def test_native_go_vendoring_preserves_sources_and_rejects_downgrades(
    tmp_path: Path, current: str, list_failure: bool, success: bool,
    preparation_failure: str,
) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    go = binary / "go"
    go.write_text(
        '#!/bin/bash\n'
        'printf "%s\\n" "$*" >> "$GO_LOG"\n'
        'if [[ "$1" == list ]]; then\n'
        '  if [[ "$LIST_FAILURE" == true ]]; then exit 1; fi\n'
        '  printf "%s\\n" "$MODULES"\n'
        'elif [[ "$1 $2" == "mod tidy" ]]; then\n'
        '  if [[ "$PREPARATION_FAILURE" == tidy ]]; then exit 1; fi\n'
        '  touch module-graph-complete\n'
        'elif [[ "$1 $2 $3" == "mod download all" ]]; then\n'
        '  if [[ "$PREPARATION_FAILURE" == download ]]; then exit 1; fi\n'
        '  touch checksums-complete\n'
        'elif [[ "$1 $2" == "mod vendor" ]]; then\n'
        '  if [[ ! -f module-graph-complete ]]; then\n'
        '    echo "updates to go.mod needed" >&2; exit 1\n'
        '  fi\n'
        '  if [[ ! -f checksums-complete ]]; then\n'
        '    echo "missing go.sum entry" >&2; exit 1\n'
        '  fi\n'
        '  mkdir -p vendor; printf "retained source\\n" > vendor/module.go\n'
        'fi\n'
    )
    go.chmod(0o755)
    (tmp_path / "go.mod").write_text("module example.test/application\n")
    (tmp_path / "go.sum").touch()
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"golang.org/x/net": "v0.60.0"}))
    archive = tmp_path / "corresponding-source.tar.gz"
    archive.touch()
    log = tmp_path / "go.log"
    modules = {"Path": "golang.org/x/net", "Version": current} if current else {}
    env = {
        **os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "GO_LOG": str(log),
        "MODULES": json.dumps(modules), "LIST_FAILURE": str(list_failure).lower(),
        "PREPARATION_FAILURE": preparation_failure,
    }
    command = ["bash", str(ROOT / "images/rpm-security/go-vendor.sh"),
               str(pins), str(archive)]
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert (result.returncode == 0) == (success and not preparation_failure), result.stderr
    commands = log.read_text().splitlines()
    if success and preparation_failure:
        assert archive.stat().st_size == 0
        assert "mod vendor" not in commands
        if preparation_failure == "tidy":
            assert "mod download all" not in commands
        return
    if not success:
        assert archive.stat().st_size == 0
        assert not any(command.startswith("get ") for command in commands)
        if not list_failure:
            assert "Refusing to downgrade" in result.stderr
        return
    assert ("get golang.org/x/net@v0.60.0" in commands) == bool(current)
    assert commands.index("mod tidy") < commands.index("mod download all")
    assert commands.index("mod download all") < commands.index("mod vendor")
    assert archive.stat().st_size > 0
    (tmp_path / "vendor/obsolete.go").touch()
    restored = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert restored.returncode == 0, restored.stderr
    assert log.read_text().splitlines() == commands
    assert not (tmp_path / "vendor/obsolete.go").exists()
    assert (tmp_path / "vendor/module.go").read_text() == "retained source\n"


def test_podman_recipe_uses_module_relative_build_targets() -> None:
    prepare = (ROOT / "images/rpm-security/prepare.sh").read_text()
    adaptations = prepare.split('if [[ "$package" == podman ]]; then\n', 1)[1].split(
        "\nfi", 1
    )[0]
    recipe = (
        "Source0: https://%{import_path}/archive/%{commit0}/source.tar.gz\n"
        'LDFLAGS="-X %{import_path}/libpod/define.buildInfo=123"\n'
        "%gobuild -o bin/rootlessport %{import_path}/cmd/rootlessport\n"
        "%gobuild -o bin/podman %{import_path}/cmd/%{name}\n"
        "%gobuild -o bin/quadlet %{import_path}/cmd/quadlet\n"
        "%gobuild -o bin/podman-testing %{import_path}/cmd/podman-testing\n"
        "%gobuild -o bin/dnsname github.com/containers/dnsname/plugins/meta/dnsname\n"
    )
    adapted = recipe
    for line in adaptations.splitlines():
        if line.strip().startswith("sed -i 's|%{import_path}/"):
            command = shlex.split(line)
            result = subprocess.run(
                ["sed", "-e", command[2]], input=adapted,
                capture_output=True, text=True, check=True, timeout=10,
            )
            adapted = result.stdout
    assert adapted == (
        recipe.replace("%{import_path}/cmd/", "./cmd/")
        .replace("%{import_path}/libpod/", "%{import_path}/v5/libpod/")
    )
    assert "%{import_path}/cmd/" not in adapted


@pytest.mark.parametrize("valid_macro", [True, False])
def test_skopeo_recipe_uses_standard_go_fips_crypto(
    tmp_path: Path, valid_macro: bool
) -> None:
    prepare = (ROOT / "images/rpm-security/prepare.sh").read_text()
    adaptations = prepare.split('if [[ "$package" == skopeo ]]; then\n', 1)[1].split(
        "\nfi", 1
    )[0]
    recipe = (
        '%if %{defined fips}\nexport BUILDTAGS="$BUILDTAGS libtrust_openssl"\n%endif\n'
        '%gobuild -o bin/%{name} ./cmd/%{name}\n'
    )
    macro = (
        'GOAMD64=v2 go build -buildmode pie -tags="rpm_crashtraceback libtrust_openssl'
        ' ${BUILDTAGS-}" -ldflags "-linkmode=external" $(printf "\\\\n") %{?**};'
    ) if valid_macro else "%{macrobody:gobuild}"
    rpm = tmp_path / "rpm"
    rpm.write_text('#!/bin/bash\nprintf "%s\\n" "$TEST_MACRO"\n')
    rpm.chmod(0o755)
    spec = tmp_path / "skopeo.spec"
    spec.write_text(recipe)
    result = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", adaptations],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "TEST_MACRO": macro, "spec": str(spec)},
        capture_output=True, text=True, timeout=10,
    )
    if not valid_macro:
        assert result.returncode != 0
        assert "missing Go RPM build macro" in result.stderr
        return
    assert result.returncode == 0, result.stderr
    assert spec.read_text() == (
        "%define gobuild(o:) \\\n"
        + macro.replace(" libtrust_openssl", "").replace("\\", "\\\\") + "\n\n"
        + recipe.replace(" libtrust_openssl", "")
    )


def test_source_rpm_compilation_and_checks_are_unprivileged() -> None:
    dockerfile = (ROOT / "images/rpm-security/Dockerfile").read_text()
    builder = dockerfile.split("FROM builder-base AS builder\n", 1)[1].split(
        "FROM scratch AS artifacts", 1
    )[0]
    assert builder.index("dnf -y") < builder.index("USER 10001")
    assert "useradd --uid 10001 --create-home aax-builder" in builder
    assert "chown -R aax-builder:aax-builder /build" in builder
    assert "ENV HOME=/home/aax-builder" in builder
    assert builder.index("USER 10001") < builder.index("RUN bash /aax/build.sh")
    assert "USER root" not in builder
    build = (ROOT / "images/rpm-security/build.sh").read_text()
    assert "rpmbuild -ba" in build
    assert "--nocheck" not in build


def test_downstream_dependency_manifests_are_discoverable() -> None:
    toolchain_spec = ROOT / "images/rpm-security/go-toolchain.spec"
    assert toolchain_spec.is_file()
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(toolchain_spec)],
        cwd=ROOT, capture_output=True, text=True, timeout=10,
    )
    assert tracked.returncode == 0, "The Go RPM recipe must be tracked for CI builds"
    updates = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())["updates"]
    for ecosystem, paths in (
        ("docker", [ROOT / "images" / name for name in (
            "awx-ee-runtime", "dab-security", "drools-runtime", "galaxy-runtime",
            "hub-security", "receptor-runtime", "rpm-security", "runtime-security",
            "ee-base/pip-security",
        )]),
        ("pip", [ROOT / "images" / name for name in (
            "dab-security", "runtime-security", "ee-base/pip-security",
        )]),
    ):
        directories = {
            directory for update in updates if update["package-ecosystem"] == ecosystem
            for directory in update.get("directories", [])
        }
        for path in paths:
            assert "/" + path.relative_to(ROOT).as_posix() in directories
            if ecosystem == "pip":
                assert list(path.glob("requirements*.txt"))


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
