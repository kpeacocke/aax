"""Execute publication and vulnerability-gate scripts without registry writes."""

import json
import hashlib
import io
import os
from pathlib import Path
import shlex
import subprocess
import runpy
import tarfile
import zipfile

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/publish-devel.yml").read_text())
JOBS = WORKFLOW["jobs"]
STEPS = [step for job in JOBS.values() for step in job["steps"]]
IMAGES = [
    "awx",
    "awx-ee",
    "receptor",
    "ansible-rulebook",
    "galaxy-ng",
    "gateway",
    "eda-controller",
    "eda-podman",
    "eda-decision-environment",
]


AWX_PRODUCTION_CHECK = '''def assert_production_settings(settings: Dynaconf, settings_dir: str, settings_file_path: str):  # pragma: no cover
    """Ensure at least one setting file has been loaded in production mode.
    Current systems will require /etc/tower/settings.py and
    new systems will require /etc/ansible-automation-platform/*.yaml
    """
    if "production" not in settings.current_env.lower():
        return

    required_settings_paths = [
        os.path.dirname(settings_file_path),
        "/etc/ansible-automation-platform/",
        settings_dir,
    ]

    for path in required_settings_paths:
        if any([path in os.path.dirname(f) for f in settings._loaded_files]):
            break
    else:
        from django.core.exceptions import ImproperlyConfigured  # noqa

        msg = 'No AWX configuration found at %s.' % required_settings_paths
        msg += '\\nDefine the AWX_SETTINGS_FILE environment variable to '
        msg += 'specify an alternate path.'
        raise ImproperlyConfigured(msg)
'''


@pytest.mark.parametrize(
    "mutation",
    ["unchanged", "missing", "duplicate", "predicate", "environment", "paths", "rejection"],
)
def test_awx_dynaconf_patch_requires_exact_production_check(
    tmp_path: Path, mutation: str
) -> None:
    patch = runpy.run_path(str(ROOT / "images/runtime-security/patch_awx_dynaconf.py"))["patch"]
    source = tmp_path / "functions.py"
    original = AWX_PRODUCTION_CHECK
    if mutation == "missing":
        original = ""
    elif mutation == "duplicate":
        original *= 2
    elif mutation == "predicate":
        original = original.replace("path in os.path.dirname(f)", "True")
    elif mutation == "environment":
        original = original.replace('"production" not in', '"production" in')
    elif mutation == "paths":
        original = original.replace("os.path.dirname(settings_file_path)", '"/tmp"')
    elif mutation == "rejection":
        original = original.replace("raise ImproperlyConfigured(msg)", "return")
    source.write_text(original)
    if mutation == "unchanged":
        patch(source)
        assert source.read_text() == original.replace(
            "settings._loaded_files", "settings.__core__.config.loaded_files"
        )
        with pytest.raises(ValueError, match="Unexpected AWX"):
            patch(source)
    else:
        with pytest.raises(ValueError, match="Unexpected AWX"):
            patch(source)
        assert source.read_text() == original


def test_final_awx_image_checks_production_settings_after_dynaconf_patch() -> None:
    dockerfile = (ROOT / "images/runtime-security/DAB.Dockerfile").read_text()
    assert dockerfile.index('"${PYTHON}" /tmp/aax-patch-awx-dynaconf.py') < dockerfile.index(
        "AWX_MODE=production"
    )
    assert "DJANGO_SETTINGS_MODULE=awx.settings" in dockerfile
    assert 'AWX_SETTINGS_FILE="$settings_file"' in dockerfile
    assert "settings.AAX_TEST" in dockerfile
    assert "AWX_SETTINGS_DIR=/tmp/aax-missing-settings-dir" in dockerfile  # pragma: allowlist secret
    assert "grep -F 'No AWX configuration found at'" in dockerfile


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
    for image in IMAGES:
        result = subprocess.run(
            ["bash", "-c", script("Give security reports distinct analysis identities")],
            cwd=tmp_path, env={**os.environ, "BUNDLE_IMAGE": image},
            capture_output=True, text=True, timeout=10,
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
    runtime = (ROOT / "scripts/patch-bundle-image.sh").read_text()
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


def bundle_evidence(path: Path) -> dict[str, str]:
    """Create complete run-bound evidence; production verification is not stubbed."""
    (path / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    (path / "images/rpm-security").mkdir(parents=True)
    reports = path / "bundle-reports"
    reports.mkdir()
    env = {
        **os.environ, "IMAGE_OWNER": "TestOwner", "REGISTRY": "ghcr.io",
        "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "101", "GITHUB_RUN_ATTEMPT": "1",
        "IMAGE_TAG": "devel-" + "a" * 40 + "-101-1", "GITHUB_REF": "refs/heads/main",
        "PUSH_MUTABLE": "false", "GITHUB_STEP_SUMMARY": str(path / "summary"),
    }
    for stage, names in (("raw", IMAGES), ("gated", IMAGES),
                         ("tools", ["pip-security", "go-security"])):
        directory = path / "candidate-maps" / stage
        directory.mkdir(parents=True)
        for index, name in enumerate(names, 1):
            descriptor = {
                "name": name, "stage": stage, "repository": f"ghcr.io/testowner/aax-{name}",
                "digest": f"sha256:{index:064x}", "image_id": f"sha256:{index + 100:064x}",
                "aax_revision": env["GITHUB_SHA"], "run_id": "101", "run_attempt": "1",
            }
            text = json.dumps(descriptor)
            (directory / f"{name}.json").write_text(text)
            if stage != "gated":
                continue
            (reports / f"{name}-gate.json").write_text(text)
            (reports / f"{name}.json").write_text(json.dumps({
                "SchemaVersion": 2, "Results": [],
                "Metadata": {"ImageID": descriptor["image_id"]},
            }))
            (reports / f"{name}-grype.json").write_text(
                json.dumps(grype_report(descriptor["image_id"]))
            )
            (reports / f"{name}.cdx.json").write_text(
                json.dumps({"bomFormat": "CycloneDX", "components": [{"name": "real-package"}]})
            )
            for suffix in (".sarif", "-grype.sarif"):
                (reports / f"{name}{suffix}").write_text(
                    json.dumps({"version": "2.1.0", "runs": [
                        {"tool": {"driver": {"name": "scanner"}}, "results": []},
                    ]})
                )
    for name in ("awx", "galaxy-ng", "eda-controller"):
        (reports / f"{name}-dab-source.json").write_text(json.dumps({
            "service": name, "repository": "https://github.com/ansible/django-ansible-base",
            "revision": "c" * 40, "version": "1.2.3+aax.3",
        }))
    (reports / "sources.json").write_text(json.dumps({
        "aax_revision": env["GITHUB_SHA"], "image_tag": env["IMAGE_TAG"],
        "sources": [{"name": name, "revision": "b" * 40} for name in IMAGES[:5]],
    }))
    (reports / "runtime-gate.json").write_text(json.dumps({
        key: json.loads((path / "candidate-maps/gated" / f"{name}.json").read_text())
        for key, name in (
            ("podman", "eda-podman"), ("decision", "eda-decision-environment"),
            ("controller", "eda-controller"),
        )
    }))
    (reports / "eda-rulebook-smoke.log").write_text("AAX_DECISION_SECURITY_SMOKE_PASSED\n")
    (reports / "nested-runtime.log").write_text("HTTPS/range debug passed\n")
    (reports / "eda-controller-recovery.log").write_text("AAX_CONTROLLER_ACTIVATION_RECOVERY_PASSED\n")
    (reports / "eda-controller-acceptance.json").write_text(json.dumps({
        "status": "running", "git_hash": env["GITHUB_SHA"],
        "activation_id": 1, "instance_id": 2, "last_log_id": 3,
    }))
    packages = json.loads((ROOT / "images/rpm-security/sources.json").read_text())
    source_bytes = b"pinned signed source RPM"
    for spec in packages.values():
        spec["sha256"] = hashlib.sha256(source_bytes).hexdigest()
    (path / "images/rpm-security/sources.json").write_text(json.dumps(packages))
    with tarfile.open(path / "native-rpms.tar.gz", "w:gz") as archive:
        info = tarfile.TarInfo("rpm-security/install.sh")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"true"))
        for package in packages:
            for member in ("signed-source.src.rpm", "source-signature.txt",
                           "srpms/patched.src.rpm", "rpms/patched.rpm"):
                payload = (
                    source_bytes if member == "signed-source.src.rpm"
                    else b"digests signatures OK"
                )
                info = tarfile.TarInfo(f"rpm-security/packages/{package}/{member}")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
    return env


@pytest.mark.parametrize("mutable", [True, False])
@pytest.mark.parametrize("fail_push", [True, False])
def test_publisher_never_skips_fresh_images(
    tmp_path: Path, mutable: bool, fail_push: bool
) -> None:
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\n'
        'printf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
        'if [[ "$3" == create && "$FAIL_PUSH" == true ]]; then exit 1; fi\n'
        'if [[ "$3" == inspect ]]; then\n'
        '  name="${4##*/aax-}"; name="${name%%:*}"; [[ "$name" != pulp ]] || name=galaxy-ng\n'
        '  jq "{digest: .digest}" "candidate-maps/gated/$name.json"\nfi\n'
    )
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    env = {
        **bundle_evidence(tmp_path),
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "FAIL_PUSH": str(fail_push).lower(),
        "PUSH_MUTABLE": str(mutable).lower(),
    }
    result = subprocess.run(
        ["bash", "-c", script("Tag and push bundle")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    commands = log.read_text().splitlines() if log.exists() else []
    pushes = [command for command in commands if command.startswith("buildx imagetools create ")]
    if fail_push:
        assert result.returncode != 0
        assert len(pushes) == 1
        assert all("--tag ghcr.io/testowner/aax-awx:devel " not in command for command in pushes)
        return
    assert result.returncode == 0, result.stderr
    assert len(pushes) == (20 if mutable else 10)
    assert all(f":{env['IMAGE_TAG']} " in command for command in pushes[:10])
    assert len({command for command in pushes[:10]}) == 10
    assert len(list((tmp_path / "bundle-reports").glob("*-manifest.json"))) == 10
    if mutable:
        assert all(":devel " in command for command in pushes[10:])
    for command in pushes:
        assert "--prefer-index=false" in command
        assert "@sha256:" in command
    assert not any(command.startswith(("build ", "pull ", "tag ", "push ")) for command in commands)


def test_staged_jobs_build_independently_and_reuse_exact_dependencies() -> None:
    assert JOBS["build-images"]["needs"] == "resolve-sources"
    assert JOBS["build-images"]["strategy"]["matrix"]["image"] == IMAGES
    assert JOBS["native-tools"]["needs"] == "build-images"
    assert JOBS["gate-foundations"]["needs"] == "native-tools"
    assert JOBS["gate-images"]["needs"] == ["native-tools", "gate-foundations"]
    gated = [
        image for job in ("gate-foundations", "gate-images")
        for image in JOBS[job]["strategy"]["matrix"]["image"]
    ]
    assert sorted(gated) == sorted(IMAGES)
    for job in ("build-images", "gate-foundations", "gate-images"):
        assert JOBS[job]["strategy"]["fail-fast"] is False
        assert JOBS[job]["runs-on"] == "ubuntu-24.04"
    builds = [step["run"] for step in STEPS if "build-bundle-image.sh" in step.get("run", "")]
    assert len(builds) == 1
    assert 'bash scripts/build-bundle-image.sh "$BUNDLE_IMAGE"' in builds[0]
    assert "set -euo pipefail" in builds[0]
    native = script("Build shared signed source RPMs and FIPS compiler once")
    assert native.count("bash scripts/build-rpm-security.sh") == 1
    assert "RPM_RETAIN_COMPILER=true bash scripts/build-rpm-security.sh" in native
    rpm = (ROOT / "scripts/build-rpm-security.sh").read_text()
    assert rpm.index('push go-security tools') < rpm.index("while IFS= read -r package")
    restore = script("Restore shared artifacts and this image only")
    assert 'pull "$BUNDLE_IMAGE" raw' in restore
    assert "pull receptor gated" in restore and "pull ansible-rulebook gated" in restore
    assert "ansible-rulebook:devel ansible-rulebook:patched" in restore
    for step in STEPS:
        if step.get("uses", "").startswith("actions/download-artifact@"):
            assert "${{ github.run_attempt }}" in str(step["with"])
        if step.get("uses", "").startswith("actions/checkout@"):
            assert step["with"]["persist-credentials"] is False
    assert "git ls-remote" not in (ROOT / "scripts/build-bundle-image.sh").read_text()


def test_runtime_artifact_preserves_workspace_relative_evidence_layout() -> None:
    preserve = next(
        step for step in JOBS["validate-runtime"]["steps"]
        if step.get("name") == "Preserve runtime evidence on failure"
    )
    paths = [Path(path) for path in preserve["with"]["path"].splitlines()]
    assert Path(os.path.commonpath([str(path.parent) for path in paths])) == Path(".")
    assert set(paths) == {
        Path("candidate-maps/gated/eda-podman.json"),
        Path("candidate-maps/gated/eda-decision-environment.json"),
        Path("candidate-maps/gated/eda-controller.json"),
        Path("bundle-reports/nested-runtime.log"),
        Path("bundle-reports/eda-rulebook-smoke.log"),
        Path("bundle-reports/runtime-gate.json"),
        Path("bundle-reports/eda-controller-acceptance.json"),
        Path("bundle-reports/eda-controller-acceptance.log"),
        Path("bundle-reports/eda-controller-recovery.log"),
    }
    assert preserve["if"] == "always()"


@pytest.mark.parametrize("mismatch,fail_push", [(False, False), (True, False), (False, True)])
def test_candidate_transfer_records_exact_manifest_and_rejects_substitution(
    tmp_path: Path, mismatch: bool, fail_push: bool
) -> None:
    env = bundle_evidence(tmp_path)
    descriptor = tmp_path / "candidate-maps/gated/awx.json"
    descriptor.unlink()
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nset -eu\n'
        'echo "$*" >> "$DOCKER_LOG"\n'
        'case "$1 $2" in\n'
        '  "image inspect") echo "$IMAGE_ID" ;;\n'
        '  "push "*) [[ "$FAIL_PUSH" != true ]] ;;\n'
        '  "buildx imagetools")\n'
        '    if [[ "$4" == --raw ]]; then\n'
        '      jq -n --arg id "$CONFIG_ID" "{config: {digest: \\$id}}"\n'
        '    else jq -n --arg digest "$MANIFEST_ID" "{digest: \\$digest}"; fi ;;\n'
        'esac\n'
    )
    docker.chmod(0o755)
    image_id = "sha256:" + "c" * 64
    log = tmp_path / "docker.log"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/bundle-candidate.sh"), "push", "awx", "gated"],
        cwd=tmp_path, env={
            **env, "PATH": f"{tmp_path}:{os.environ['PATH']}", "DOCKER_LOG": str(log),
            "IMAGE_ID": image_id, "CONFIG_ID": "sha256:" + "d" * 64 if mismatch else image_id,
            "MANIFEST_ID": "sha256:" + "e" * 64, "FAIL_PUSH": str(fail_push).lower(),
        }, capture_output=True, text=True, timeout=30,
    )
    assert (result.returncode == 0) == (not (mismatch or fail_push)), result.stderr
    assert descriptor.exists() == (not (mismatch or fail_push))
    assert "candidate-101-1-gated" in log.read_text()
    assert ":devel-" not in log.read_text()
    if not (mismatch or fail_push):
        identity = json.loads(descriptor.read_text())
        assert identity["image_id"] == image_id
        assert identity["digest"] == "sha256:" + "e" * 64
        assert identity["run_attempt"] == "1"


@pytest.mark.parametrize("identity", ["config", "manifest", "unrelated", "wrong-config"])
def test_candidate_pull_verifies_config_before_accepting_docker_identity(
    tmp_path: Path, identity: str,
) -> None:
    env = bundle_evidence(tmp_path)
    descriptor = json.loads((tmp_path / "candidate-maps/gated/awx.json").read_text())
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nset -eu\n'
        'case "$1 $2" in\n'
        '  "buildx imagetools") jq -n --arg id "$CONFIG_ID" \'{config: {digest: $id}}\' ;;\n'
        '  "image inspect") echo "$LOADED_ID" ;;\n'
        'esac\n'
    )
    docker.chmod(0o755)
    config = descriptor["image_id"]
    loaded = descriptor["digest"] if identity == "manifest" else config
    if identity == "unrelated":
        loaded = "sha256:" + "f" * 64
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/bundle-candidate.sh"), "pull", "awx", "gated"],
        cwd=tmp_path,
        env={**env, "PATH": f"{tmp_path}:{os.environ['PATH']}", "LOADED_ID": loaded,
             "CONFIG_ID": "sha256:" + "e" * 64 if identity == "wrong-config" else config},
        capture_output=True, text=True, timeout=30,
    )
    assert (result.returncode == 0) == (identity in ("config", "manifest")), result.stderr


@pytest.mark.parametrize("identity", ["config", "manifest"])
def test_publication_verifies_same_trivy_identities_as_scan_gate(
    tmp_path: Path, identity: str,
) -> None:
    env = bundle_evidence(tmp_path)
    descriptor = json.loads((tmp_path / "candidate-maps/gated/awx.json").read_text())
    report = tmp_path / "bundle-reports/awx.json"
    data = json.loads(report.read_text())
    data["Metadata"]["ImageID"] = descriptor["digest" if identity == "manifest" else "image_id"]
    report.write_text(json.dumps(data))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/verify-bundle-evidence.sh")], cwd=tmp_path,
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("damage", [
    "missing-map", "extra-map", "empty-map", "mutable-digest", "wrong-run", "wrong-attempt",
    "wrong-owner", "wrong-name", "wrong-stage", "wrong-aax", "missing-raw", "missing-tool",
    "missing-native", "missing-sources", "missing-trivy", "missing-grype", "missing-sbom",
    "empty-sarif", "mismatched-trivy", "mismatched-grype", "missing-gate",
    "mismatched-runtime", "missing-runtime", "missing-range-debug", "fixable-vulnerability",
    "empty-native", "substituted-source-rpm",
    "empty-sbom", "missing-dab-provenance", "mutable-dab-provenance",
    "missing-controller-result", "missing-recovery-marker", "wrong-controller-git",
])
def test_incomplete_or_substituted_evidence_blocks_all_registry_writes(
    tmp_path: Path, damage: str
) -> None:
    env = bundle_evidence(tmp_path)
    descriptor = tmp_path / "candidate-maps/gated/awx.json"
    data = json.loads(descriptor.read_text())
    paths = {
        "missing-map": descriptor, "missing-raw": tmp_path / "candidate-maps/raw/awx.json",
        "missing-tool": tmp_path / "candidate-maps/tools/go-security.json",
        "missing-native": tmp_path / "native-rpms.tar.gz",
        "missing-sources": tmp_path / "bundle-reports/sources.json",
        "missing-trivy": tmp_path / "bundle-reports/awx.json",
        "missing-grype": tmp_path / "bundle-reports/awx-grype.json",
        "missing-sbom": tmp_path / "bundle-reports/awx.cdx.json",
        "missing-gate": tmp_path / "bundle-reports/awx-gate.json",
        "missing-runtime": tmp_path / "bundle-reports/runtime-gate.json",
        "missing-range-debug": tmp_path / "bundle-reports/eda-rulebook-smoke.log",
        "missing-dab-provenance": tmp_path / "bundle-reports/awx-dab-source.json",
        "missing-controller-result": tmp_path / "bundle-reports/eda-controller-acceptance.json",
        "missing-recovery-marker": tmp_path / "bundle-reports/eda-controller-recovery.log",
    }
    if damage in paths:
        paths[damage].unlink()
    elif damage == "wrong-controller-git":
        report = tmp_path / "bundle-reports/eda-controller-acceptance.json"
        result = json.loads(report.read_text())
        result["git_hash"] = "b" * 40
        report.write_text(json.dumps(result))
    elif damage == "empty-native":
        (tmp_path / "native-rpms.tar.gz").write_bytes(b"")
    elif damage == "empty-sbom":
        (tmp_path / "bundle-reports/awx.cdx.json").write_text(json.dumps({
            "bomFormat": "CycloneDX", "components": [],
        }))
    elif damage == "mutable-dab-provenance":
        source = tmp_path / "bundle-reports/awx-dab-source.json"
        data = json.loads(source.read_text())
        data["revision"] = "devel"
        source.write_text(json.dumps(data))
    elif damage == "substituted-source-rpm":
        sources = tmp_path / "images/rpm-security/sources.json"
        data = json.loads(sources.read_text())
        data["apr"]["sha256"] = "0" * 64
        sources.write_text(json.dumps(data))
    elif damage == "extra-map":
        descriptor.with_name("unexpected.json").write_text(descriptor.read_text())
    elif damage == "empty-map":
        descriptor.write_text("{}")
    elif damage == "empty-sarif":
        (tmp_path / "bundle-reports/awx.sarif").write_text("{}")
    elif damage.startswith("wrong-") or damage == "mutable-digest":
        field, value = {
            "wrong-run": ("run_id", "102"), "wrong-attempt": ("run_attempt", "2"),
            "wrong-owner": ("repository", "ghcr.io/attacker/aax-awx"),
            "wrong-name": ("name", "awx-ee"), "wrong-stage": ("stage", "raw"),
            "wrong-aax": ("aax_revision", "b" * 40), "mutable-digest": ("digest", "devel"),
        }[damage]
        data[field] = value
        descriptor.write_text(json.dumps(data))
    elif damage == "mismatched-runtime":
        (tmp_path / "bundle-reports/runtime-gate.json").write_text("{}")
    elif damage == "mismatched-trivy":
        report = tmp_path / "bundle-reports/awx.json"
        data = json.loads(report.read_text())
        data["Metadata"]["ImageID"] = "sha256:" + "f" * 64
        report.write_text(json.dumps(data))
    elif damage == "mismatched-grype":
        (tmp_path / "bundle-reports/awx-grype.json").write_text(json.dumps(grype_report()))
    elif damage == "fixable-vulnerability":
        report = tmp_path / "bundle-reports/awx.json"
        data = json.loads(report.read_text())
        data["Results"] = [{"Vulnerabilities": [{
            "VulnerabilityID": "BLOCK", "Severity": "HIGH", "FixedVersion": "1",
        }]}]
        report.write_text(json.dumps(data))
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\necho registry-write >> "$DOCKER_LOG"\n')
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/promote-bundle.sh")], cwd=tmp_path,
        env={**env, "DOCKER_LOG": str(log), "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0, damage
    assert not log.exists(), damage


def test_native_output_recipe_preserves_original_signed_source_rpms() -> None:
    native = (ROOT / "scripts/build-rpm-security.sh").read_text()
    assert "COPY --from=builder /build/source.src.rpm /signed-source.src.rpm" in native
    assert '-f "$output/Artifacts.Dockerfile"' in native
    assert 'test -s "$output/packages/$package/signed-source.src.rpm"' in native
    assert '--build-arg GO_IMAGE=aax/go-security:devel' in native


def test_native_package_failure_retains_compiler_identity_and_build_logs(tmp_path: Path) -> None:
    env = bundle_evidence(tmp_path)
    descriptor = tmp_path / "candidate-maps/tools/go-security.json"
    descriptor.unlink()
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nset -eu\n'
        'echo "$*" >> "$DOCKER_LOG"\n'
        'case "$1 $2" in\n'
        '  "build "*) [[ "$*" != *"--output "* ]] || exit 42 ;;\n'
        '  "image inspect") echo "$IMAGE_ID" ;;\n'
        '  "buildx imagetools")\n'
        '    if [[ "$4" == --raw ]]; then\n'
        '      jq -n --arg id "$IMAGE_ID" "{config: {digest: \\$id}}"\n'
        '    else jq -n --arg digest "$MANIFEST_ID" "{digest: \\$digest}"; fi ;;\n'
        'esac\n'
    )
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    output = tmp_path / "native-output"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/build-rpm-security.sh"), str(output)], cwd=tmp_path,
        env={**env, "RPM_RETAIN_COMPILER": "true", "DOCKER_LOG": str(log),
             "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "IMAGE_ID": "sha256:" + "a" * 64, "MANIFEST_ID": "sha256:" + "b" * 64},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 42
    assert descriptor.is_file()
    assert (output / "logs/bootstrap.log").is_file()
    assert (output / "logs/compiler.log").is_file()
    assert (output / "logs/apr.log").is_file()
    commands = log.read_text().splitlines()
    push = next(index for index, command in enumerate(commands) if command.startswith("push "))
    package_build = next(index for index, command in enumerate(commands) if "--output " in command)
    assert push < package_build
    assert "/Artifacts.Dockerfile" in commands[package_build]


def test_branch_dispatch_retains_candidates_without_any_promotion(tmp_path: Path) -> None:
    env = bundle_evidence(tmp_path)
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\necho registry-write >> "$DOCKER_LOG"\nexit 1\n')
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/promote-bundle.sh")], cwd=tmp_path,
        env={**env, "GITHUB_REF": "refs/heads/fix/staged-upstream-bundle",
             "PUSH_MUTABLE": "true", "DOCKER_LOG": str(log),
             "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert not log.exists()
    assert "retains candidates" in result.stdout


@pytest.mark.parametrize(
    "fail_scanner,mismatch,fixable",
    [(False, False, False), (True, False, False), (False, True, False), (False, False, True)],
)
@pytest.mark.parametrize("trivy_identity", ["config", "digest", "invalid"])
def test_exact_digest_scans_require_both_scanners_before_receipt(
    tmp_path: Path, fail_scanner: bool, mismatch: bool, fixable: bool, trivy_identity: str
) -> None:
    env = bundle_evidence(tmp_path)
    receipt = tmp_path / "bundle-reports/awx-gate.json"
    receipt.unlink()
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "trivy").write_text(
        '#!/bin/bash\nset -eu\n'
        'echo "$*" >> "$SCANNER_LOG"\n'
        'if [[ "$1" == convert ]]; then\n'
        '  while [[ "$1" != --output ]]; do shift; done\n'
        '  printf \'{"version":"2.1.0","runs":[]}\\n\' > "$2"\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "$*" == *"--format cyclonedx"* ]]; then\n'
        '  while [[ "$1" != --output ]]; do shift; done\n'
        '  cp "$CYCLONEDX_SOURCE" "$2"\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "$1" != image ]]; then exit 0; fi\n'
        'while [[ "$1" != --output ]]; do shift; done\n'
        'cp "$TRIVY_SOURCE" "$2"\n'
    )
    (binary / "grype").write_text(
        '#!/bin/bash\nset -eu\n'
        'echo "$*" >> "$SCANNER_LOG"\n'
        '[[ "$FAIL_SCANNER" != true ]] || exit 1\n'
        'while [[ "$1" != json=* ]]; do shift; done\n'
        'cp "$GRYPE_SOURCE" "${1#json=}"\n'
    )
    for executable in binary.iterdir():
        executable.chmod(0o755)
    trivy_source = tmp_path / "trivy-source.json"
    data = json.loads((tmp_path / "bundle-reports/awx.json").read_text())
    descriptor = json.loads((tmp_path / "candidate-maps/gated/awx.json").read_text())
    reference = descriptor["repository"] + "@" + descriptor["digest"]
    if trivy_identity == "digest":
        data["Metadata"]["ImageID"] = descriptor["digest"]
    elif trivy_identity == "invalid":
        data["Metadata"]["ImageID"] = "sha256:" + "f" * 64
    if fixable:
        data["Results"] = [{"Vulnerabilities": [{
            "VulnerabilityID": "BLOCK", "Severity": "CRITICAL", "FixedVersion": "1",
        }]}]
    trivy_source.write_text(json.dumps(data))
    cdx_source = tmp_path / "cyclonedx-source.json"
    cdx_source.write_text(json.dumps({
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "metadata": {"component": {"type": "container", "name": reference}},
        "components": [{
            "bom-ref": "pkg:pypi/example-vulnerable@1.0",
            "name": "example-vulnerable",
            "version": "1.0",
        }],
        "vulnerabilities": [{
            "id": "TEST-CVE",
            "affects": [{"ref": "pkg:pypi/example-vulnerable@1.0"}],
        }],
    }))
    grype_source = tmp_path / "grype-source.json"
    config_image_id = descriptor["image_id"]
    grype_source.write_text(json.dumps(grype_report(
        "sha256:" + "f" * 64 if mismatch else config_image_id
    )))
    log = tmp_path / "scanner.log"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/scan-bundle-image.sh"), "awx"], cwd=tmp_path,
        env={**env, "PATH": f"{binary}:{os.environ['PATH']}", "RUNNER_TEMP": str(binary),
             "SCANNER_LOG": str(log), "TRIVY_SOURCE": str(trivy_source),
             "CYCLONEDX_SOURCE": str(cdx_source),
             "GRYPE_SOURCE": str(grype_source), "FAIL_SCANNER": str(fail_scanner).lower()},
        capture_output=True, text=True, timeout=30,
    )
    should_fail = fail_scanner or mismatch or fixable or trivy_identity == "invalid"
    assert (result.returncode == 0) == (not should_fail), result.stderr
    assert receipt.exists() == (not should_fail)
    commands = log.read_text().splitlines()
    assert any(reference in command and "--image-src docker" in command for command in commands)
    cdx_command = next(command for command in commands if "--format cyclonedx" in command)
    assert "--scanners vuln" in cdx_command and reference in cdx_command
    assert any(f"docker:{reference}" in command for command in commands)
    cdx_report = json.loads((tmp_path / "bundle-reports/awx.cdx.json").read_text())
    assert cdx_report["bomFormat"] == "CycloneDX"
    assert cdx_report["metadata"]["component"]["name"] == reference
    assert cdx_report["components"][0]["name"] == "example-vulnerable"
    assert cdx_report["vulnerabilities"][0]["affects"][0]["ref"] == (
        "pkg:pypi/example-vulnerable@1.0"
    )
    assert cdx_report["vulnerabilities"][0]["affects"][0]["ref"] == (
        cdx_report["components"][0]["bom-ref"]
    )
    assert any("convert --format sarif" in command for command in commands)
    assert (tmp_path / "bundle-reports/awx.sarif").exists()


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
        cwd=tmp_path, env={**os.environ, "BUNDLE_IMAGE": "awx"},
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode != 0) == blocked, result.stderr


def test_bundle_scan_precedes_publication() -> None:
    names = [step.get("name", "") for step in JOBS["gate-images"]["steps"]]
    assert names.index("Scan exact bundle images") < names.index(
        "Gate on fixable high and critical bundle vulnerabilities"
    )
    assert JOBS["publish"]["needs"] == [
        "resolve-sources", "build-images", "native-tools",
        "gate-foundations", "gate-images", "validate-runtime",
    ]
    assert "if" not in JOBS["publish"]
    scan = (ROOT / "scripts/scan-bundle-image.sh").read_text()
    assert "set -euo pipefail" in scan
    assert '"$RUNNER_TEMP/grype"' in scan
    assert 'json=bundle-reports/$name-grype.json' in scan
    assert 'sarif=bundle-reports/$name-grype.sarif' in scan
    assert '"docker:$reference"' in scan and '--output "bundle-reports/$name.json" "$reference"' in scan
    assert ".Metadata.ImageID == $id" in scan and ".source.target.imageID == $id" in scan
    assert "sha256sum --check -" in script("Install supplemental OS scanner")


def test_artifact_and_trivy_cli_pins_match_supported_runtimes() -> None:
    download = (
        "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333"
    )
    upload = "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
    downloads = list({
        id(step): step for step in STEPS
        if step.get("uses", "").startswith("actions/download-artifact@")
    }.values())
    uploads = [step for step in STEPS if step.get("uses", "").startswith("actions/upload-artifact@")]
    assert len(downloads) == 7
    assert all(step["uses"] == download for step in downloads)
    assert all(step["uses"] == upload for step in uploads)
    assert all(job["runs-on"] == "ubuntu-24.04" for job in JOBS.values())
    assert all("${{ github.run_attempt }}" in str(step["with"]) for step in downloads)
    named_downloads = [step["with"] for step in downloads if "name" in step.get("with", {})]
    pattern_downloads = [step["with"] for step in downloads if "pattern" in step.get("with", {})]
    assert len(named_downloads) == 3
    assert len(pattern_downloads) == 4
    assert sorted(item["pattern"] for item in pattern_downloads) == sorted([
        "bundle-input-*-${{ github.run_attempt }}",
        "bundle-input-*-${{ github.run_attempt }}",
        "bundle-gate-eda-*-${{ github.run_attempt }}",
        "bundle-*-${{ github.run_attempt }}",
    ])
    assert all(item.get("merge-multiple") is True for item in pattern_downloads)
    assert all("path" not in item for item in downloads)
    assert any("bundle-input-sources-" in item["name"] for item in named_downloads)
    assert any("bundle-gate-receptor-" in item["name"] for item in named_downloads)
    assert any("bundle-gate-ansible-rulebook-" in item["name"] for item in named_downloads)

    expected_trivy = "v0.76.1"
    workflows = (
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/publish-images.yml",
        ".github/workflows/publish-devel.yml",
    )
    for path in workflows:
        workflow = yaml.safe_load((ROOT / path).read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                uses = step.get("uses", "")
                if uses.startswith("aquasecurity/trivy-action@"):
                    assert step.get("with", {}).get("version") == expected_trivy, path
                elif uses.startswith("aquasecurity/setup-trivy@"):
                    assert step.get("with", {}).get("version") == expected_trivy, path


def test_nested_podman_uses_explicit_local_decision_environment() -> None:
    nested_podman = script("Verify nested Podman execution and outbound HTTPS")
    image = "localhost/eda-decision-environment:devel"
    assert f"docker tag eda-decision-environment:devel {image}" in nested_podman
    assert f"docker save {image}" in nested_podman
    assert f"{image} python3.12 -c" in nested_podman
    assert '| docker exec -i aax-eda-podman-test podman load' in nested_podman
    assert "eda-decision-environment.tar" not in nested_podman
    assert "quay.io/prometheus/busybox@sha256:" in nested_podman
    assert "pull \\\n            quay.io/ansible/ansible-rulebook@" not in nested_podman
    assert JOBS["validate-runtime"]["needs"] == ["gate-foundations", "gate-images"]
    names = [step.get("name", "") for step in JOBS["validate-runtime"]["steps"]]
    assert names.index("Load only scanned runtime digests on a fresh runner") < names.index(
        "Require nested VFS disk budget"
    ) < names.index("Verify nested Podman execution and outbound HTTPS")
    assert "test \"$ready\" = true" in nested_podman
    assert "bundle-reports/runtime-gate.json" in nested_podman


@pytest.mark.parametrize("https_fails,marker", [(False, True), (True, True), (False, False)])
def test_nested_runtime_receipt_requires_https_and_real_range_debug_marker(
    tmp_path: Path, https_fails: bool, marker: bool
) -> None:
    env = bundle_evidence(tmp_path)
    receipt = tmp_path / "bundle-reports/runtime-gate.json"
    receipt.unlink()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/fixtures").symlink_to(ROOT / "tests/fixtures", target_is_directory=True)
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nset -eu\n'
        'echo "$*" >> "$DOCKER_LOG"\n'
        'case "$*" in\n'
        '  *"python3.12 -c"*) [[ "$HTTPS_FAILS" != true ]] || exit 1 ;;\n'
        '  *"--rulebook /dev/stdin"*)\n'
        '    if [[ "$MARKER" == true ]]; then echo AAX_DECISION_SECURITY_SMOKE_PASSED;\n'
        '    else echo "No range events processed"; fi ;;\n'
        '  "exec -i aax-eda-podman-test podman load") cat >/dev/null ;;\n'
        'esac\n'
    )
    docker.chmod(0o755)
    log = tmp_path / "docker.log"
    result = subprocess.run(
        ["bash", "-c", script("Verify nested Podman execution and outbound HTTPS")],
        cwd=tmp_path, env={**env, "PATH": f"{tmp_path}:{os.environ['PATH']}",
                          "DOCKER_LOG": str(log), "HTTPS_FAILS": str(https_fails).lower(),
                          "MARKER": str(marker).lower()},
        capture_output=True, text=True, timeout=30,
    )
    success = not https_fails and marker
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    assert receipt.exists() == success
    assert (tmp_path / "bundle-reports/nested-runtime.log").exists()
    commands = log.read_text()
    assert "docker system" not in commands
    assert "localhost/eda-decision-environment:devel python3.12 -c" in commands
    if success:
        assert "--rulebook /dev/stdin --shutdown-delay 1" in commands
        recorded = json.loads(receipt.read_text())
        assert recorded["podman"]["name"] == "eda-podman"
        assert recorded["decision"]["name"] == "eda-decision-environment"


@pytest.mark.parametrize(
    ("available", "success"),
    [(20 * 1024**3, True), (20 * 1024**3 - 1, False)],
)
def test_fresh_runtime_runner_requires_disk_budget_without_pruning(
    tmp_path: Path, available: int, success: bool
) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "docker").write_text(
        '#!/bin/bash\n'
        'printf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
        'exit 1\n'
    )
    (binary / "df").write_text(
        '#!/bin/bash\n'
        'printf "Filesystem 1B-blocks Used Available Use%% Mounted on\\n"\n'
        'printf "/dev/test 99999999999 0 %s 0%% /\\n" "$AVAILABLE"\n'
    )
    for executable in binary.iterdir():
        executable.chmod(0o755)
    log = tmp_path / "docker.log"
    result = subprocess.run(
        ["bash", "-c", script("Require nested VFS disk budget")],
        env={
            **os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
            "DOCKER_LOG": str(log),
            "RUNNER_TEMP": str(tmp_path), "AVAILABLE": str(available),
        },
        capture_output=True, text=True, timeout=10,
    )
    assert (result.returncode == 0) == success, result.stderr
    assert not log.exists()
    workflow = (ROOT / ".github/workflows/publish-devel.yml").read_text()
    assert "docker system df" not in workflow
    assert "docker system prune" not in workflow
    assert "timeout 180 docker buildx prune" in workflow
    if available < 20 * 1024**3:
        assert "free bytes" in result.stderr


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
    names = [step.get("name", "") for step in JOBS["gate-images"]["steps"]]
    assert names.index("Apply maintained runtime security patches") < names.index(
        "Scan exact bundle images"
    )
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/bash\nprintf "%s\\n" "$*" >> "$DOCKER_LOG"\n'
        'if [[ "$1" == run ]]; then printf "%040d 2026.10.21.1.dev2+aax.3\\n" 1; fi\n'
    )
    docker.chmod(0o755)
    (tmp_path / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    log = tmp_path / "docker.log"
    for image in IMAGES:
        result = subprocess.run(
            ["bash", "-c", script("Apply maintained runtime security patches")],
            cwd=tmp_path,
            env={
                **os.environ, "BUNDLE_IMAGE": image, "GITHUB_SHA": "test-sha",
                "PATH": f"{tmp_path}:{os.environ['PATH']}", "DOCKER_LOG": str(log),
            },
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
    commands = log.read_text().splitlines()
    assert not any("build-source-rpms" in command for command in commands)
    for name in ("awx", "awx-ee", "galaxy-ng", "eda-controller", "ansible-rulebook", "receptor"):
        rpm_build = next(
            command for command in commands if f"-t {name}:rpm-patched " in command
        )
        assert "images/rpm-security/Runtime.Dockerfile" in rpm_build
        final_build = next(command for command in commands if f"-t {name}:finalized " in command)
        assert commands.index(rpm_build) < commands.index(final_build)
    for name in ("awx", "awx-ee", "galaxy-ng", "eda-controller"):
        build = next(command for command in commands if f"-t {name}:python-patched " in command)
        assert f"BASE_IMAGE={name}:devel" in build
        assert "RUNTIME_USER=" in build and "PYTHON=" in build
    assert any("RECEPTOR_IMAGE=receptor:devel" in command for command in commands)
    assert any("images/runtime-security/EDA.Dockerfile" in command for command in commands)
    assert any("images/eda-decision-environment/Security.Dockerfile" in command for command in commands)
    assert any("images/drools-runtime" in command for command in commands)
    for name in ("awx", "galaxy-ng", "eda-controller"):
        source_build = next(
            command for command in commands if f"-t aax/dab-security:{name} " in command
        )
        assert "DAB_REVISION=" + "0" * 39 + "1" in source_build
        assert "DAB_VERSION=2026.10.21.1.dev2+aax.3" in source_build
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


@pytest.mark.parametrize(
    "database", ["TRIVY_DB_REPOSITORY", "TRIVY_JAVA_DB_REPOSITORY"]
)
def test_scanner_databases_have_independent_public_registry_fallback(database: str) -> None:
    scan = next(step for step in STEPS if step.get("name") == "Scan exact bundle images")
    artifact = "trivy-java-db:1" if database == "TRIVY_JAVA_DB_REPOSITORY" else "trivy-db:2"
    assert scan["env"][database].split(",") == [
        f"mirror.gcr.io/aquasec/{artifact}",
        f"ghcr.io/aquasecurity/{artifact}",
        f"public.ecr.aws/aquasecurity/{artifact}",
    ]


def test_normalized_sarif_is_preserved_with_original_reports() -> None:
    preserve = next(
        step for step in STEPS if step.get("name") == "Preserve bundle provenance and security reports"
    )
    assert preserve["if"] == "always()"
    assert preserve["with"]["path"].splitlines() == [
        "candidate-maps/gated/${{ matrix.image }}.json",
        "bundle-reports/${{ matrix.image }}*",
        "bundle-sarif/*-${{ matrix.image }}.sarif",
    ]
    assert preserve["with"]["retention-days"] == 90


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


def test_native_brotli_source_includes_decoder_security_backport() -> None:
    sources = json.loads((ROOT / "images/rpm-security/sources.json").read_text())
    assert sources["brotli"] == {
        "url": (
            "https://vault.almalinux.org/9.8/BaseOS/Source/Packages/"
            "brotli-1.0.9-10.el9_8.1.src.rpm"
        ),
        "sha256": "d211e0455ee313b52cbdb0078d69601e613ec2dd51049f09306f14c2fa4848b2",
        "release": "11.el9.aax.1",
    }


def test_native_go_jose_pin_covers_embedded_jwk_parser_fix() -> None:
    pins = json.loads((ROOT / "images/rpm-security/go-dependencies.json").read_text())
    assert pins["github.com/go-jose/go-jose/v4"] == "v4.1.6"
    prepare = (ROOT / "images/rpm-security/prepare.sh").read_text()
    assert "git-lfs|podman|skopeo)" in prepare
    assert "bash %{SOURCE9999} %{SOURCE9998} %{SOURCE9997}" in prepare


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
        assert 'bash scripts/scan-image-candidate.sh "$IMAGE"' in scan["run"]
        assert "@${{ steps.build.outputs.digest }}" in scan["env"]["IMAGE"]
        upload = next(step for step in steps if step.get("name") == "Upload candidate findings")
        assert upload["with"] == {"sarif_file": "image-sarif"}
        assert upload["if"] == "always() && hashFiles('image-sarif/*.sarif') != ''"
        preserve = next(step for step in steps if step.get("name") == "Preserve candidate reports")
        assert preserve["if"] == "always() && hashFiles('image-reports/*') != ''"
        assert preserve["with"]["path"].splitlines() == ["image-reports/", "image-sarif/"]
        promote = next(step for step in steps if step.get("name") == "Promote scanned candidate")
        assert promote["if"] == "github.ref == 'refs/heads/main'"
        assert promote["env"]["IMAGE"] == scan["env"]["IMAGE"]
    base = workflow["jobs"]["build-and-push"]["steps"]
    base_arg = next(step for step in base if step.get("id") == "base")
    assert "aax-ee-base@$BASE_DIGEST" in base_arg["run"]


@pytest.mark.parametrize(
    "scenario",
    ["clean", "high-amd64", "high-arm64", "scanner-failure", "invalid-json", "invalid-sarif"],
)
def test_candidate_scan_executes_both_architectures_and_fails_closed(
    tmp_path: Path, scenario: str
) -> None:
    scanner = tmp_path / "trivy"
    scanner.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['SCAN_LOG'], 'a') as log:\n"
        "    log.write(json.dumps(args) + '\\n')\n"
        "output = pathlib.Path(args[args.index('--output') + 1])\n"
        "scenario = os.environ['SCENARIO']\n"
        "if args[0] == 'convert':\n"
        "    if scenario == 'invalid-sarif' and output.stem == 'arm64':\n"
        "        output.write_text(json.dumps({'runs': []}))\n"
        "    else:\n"
        "        run = {'tool': {'driver': {'name': 'Trivy'}},\n"
        "               'automationDetails': {'id': 'duplicate/'},\n"
        "               'results': [{'ruleId': 'keep-finding'}]}\n"
        "        output.write_text(json.dumps({'version': '2.1.0', 'runs': [run, run]}))\n"
        "else:\n"
        "    arch = args[args.index('--platform') + 1].split('/')[-1]\n"
        "    if scenario == 'scanner-failure' and arch == 'arm64':\n"
        "        sys.exit(7)\n"
        "    if scenario == 'invalid-json' and arch == 'arm64':\n"
        "        output.write_text('{}')\n"
        "    else:\n"
        "        vulnerabilities = []\n"
        "        if scenario == 'high-' + arch:\n"
        "            vulnerabilities.append({'VulnerabilityID': 'TEST-CVE',\n"
        "                                    'Severity': 'HIGH', 'FixedVersion': '2'})\n"
        "        output.write_text(json.dumps({'SchemaVersion': 2, 'Results': [\n"
        "            {'Class': 'os-pkgs', 'Vulnerabilities': vulnerabilities}]}))\n"
    )
    scanner.chmod(0o755)
    image = "ghcr.io/example/candidate@sha256:" + "a" * 64
    log = tmp_path / "scanner.log"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/scan-image-candidate.sh"), image, "published-test"],
        cwd=tmp_path, capture_output=True, text=True, timeout=15,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "SCENARIO": scenario, "SCAN_LOG": str(log)},
    )
    assert (result.returncode == 0) == (scenario == "clean"), result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    scans = [call for call in calls if call[0] == "image"]
    assert [call[call.index("--platform") + 1] for call in scans] == [
        "linux/amd64", "linux/arm64",
    ]
    assert all(call[-1] == image for call in scans)
    assert (tmp_path / "image-reports/amd64.json").exists()
    assert (tmp_path / "image-reports/amd64.sarif").exists()
    identities = []
    for path in (tmp_path / "image-sarif").glob("*.sarif"):
        data = json.loads(path.read_text())
        for index, run in enumerate(data["runs"]):
            assert run["results"] == [{"ruleId": "keep-finding"}]
            assert run["automationDetails"]["id"] == f"published-test/{path.stem}/{index}/"
            identities.append(run["automationDetails"]["id"])
    assert len(identities) == len(set(identities))
    assert len(identities) == (2 if scenario in ("scanner-failure", "invalid-sarif") else 4)
    if scenario.startswith("high-"):
        assert "TEST-CVE" in result.stderr


def test_candidate_scan_rejects_mutable_tags_before_running_scanner(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/scan-image-candidate.sh"), "example:main", "test"],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
    assert "immutable sha256 image digest" in result.stderr
    assert not (tmp_path / "image-reports").exists()


@pytest.mark.parametrize("job_name", ["build-base-image", "build-and-push"])
def test_release_promotes_only_the_exact_multiarch_scanned_digest(job_name: str) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    job = workflow["jobs"][job_name]
    steps = job["steps"]
    names = [step.get("name", "") for step in steps]
    assert names.index("Scan candidate on both architectures before promotion") < names.index(
        "Promote scanned candidate"
    )
    build = next(step for step in steps if step.get("id") in ("build", "build-push"))
    assert ":release-build-${{ github.run_id }}-${{ github.run_attempt }}" in build["with"]["tags"]
    scan = next(step for step in steps if step.get("name", "").startswith("Scan candidate"))
    assert 'bash scripts/scan-image-candidate.sh "$IMAGE" release-' in scan["run"] or (
        'bash scripts/scan-image-candidate.sh "$IMAGE" "release-' in scan["run"]
    )
    assert f"@${{{{ steps.{build['id']}.outputs.digest }}}}" in scan["env"]["IMAGE"]
    upload = next(step for step in steps if step.get("name") == "Upload candidate findings")
    assert upload["with"] == {"sarif_file": "image-sarif"}
    preserve = next(step for step in steps if step.get("name") == "Preserve candidate reports")
    assert preserve["if"] == "always() && hashFiles('image-reports/*') != ''"
    promote = next(step for step in steps if step.get("name") == "Promote scanned candidate")
    assert "if" not in promote
    assert promote["env"]["IMAGE"] == scan["env"]["IMAGE"]
    if job_name == "build-and-push":
        assert "aax-ee-base@${{ needs.build-base-image.outputs.digest }}" in build["with"]["build-args"]
        sbom = next(step for step in steps if step.get("name") == "Generate SBOM")
        assert sbom["with"]["image"] == scan["env"]["IMAGE"]
        assert names.index("Attest SBOM") < names.index("Promote scanned candidate")


@pytest.mark.parametrize(
    "filename,job_name,step_name,env_name",
    [
        ("gitflow-enforce.yml", "check-branch-name", "Check branch name follows gitflow", "BRANCH_NAME"),
        ("gitflow-enforce.yml", "check-target-branch", "Check PR target follows gitflow", "SOURCE_BRANCH"),
        ("pr-automation.yml", "conventional-commits", "Advisory conventional commit check", "PR_TITLE"),
    ],
)
def test_pr_metadata_is_data_not_executable_shell(
    tmp_path: Path, filename: str, job_name: str, step_name: str, env_name: str
) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
    step = next(step for step in workflow["jobs"][job_name]["steps"] if step["name"] == step_name)
    assert "${{ github." not in step["run"]
    assert env_name in step["env"]
    payload = "$(touch INJECTED)"
    result = subprocess.run(
        ["bash", "-c", step["run"]],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
        env={**os.environ, env_name: payload, "TARGET_BRANCH": "main"},
    )
    assert not (tmp_path / "INJECTED").exists()
    assert payload in result.stdout
    assert result.returncode == (0 if env_name == "PR_TITLE" else 1)


def test_ci_validates_all_workflow_definitions() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    lint = workflow["jobs"]["lint"]["steps"]
    assert any("actionlint@v1.7.12" in step.get("run", "") for step in lint)


def test_controller_publication_has_one_maintained_owner() -> None:
    main = yaml.safe_load((ROOT / ".github/workflows/publish-images.yml").read_text())
    matrix = main["jobs"]["build-and-push"]["strategy"]["matrix"]["image"]
    assert {image["name"] for image in matrix} == {"ee-builder", "dev-tools", "gateway"}
    for filename in ("awx-ui-runtime.yml", "eda-runtime.yml"):
        workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
        assert "packages" not in workflow["permissions"]
        for job in workflow["jobs"].values():
            assert all("docker push" not in step.get("run", "") for step in job["steps"])
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    for name in (
        "pulp-api", "pulp-content", "pulp-worker", "galaxy-ng", "eda-controller",
        "eda-worker", "eda-activation-worker", "eda-ws", "eda-podman",
    ):
        assert "${DEVEL_IMAGE_TAG:-devel}" in compose["services"][name]["image"]
        assert "${AAX_VERSION" not in compose["services"][name]["image"]


@pytest.mark.parametrize(
    "scenario",
    [
        "valid", "failed", "in-progress", "wrong-workflow", "branch", "wrong-tag",
        "wrong-attempt", "unconfirmed", "invalid-id", "missing-webhook", "webhook-failure",
    ],
)
def test_deployment_requires_explicit_verified_bundle_before_webhook(
    tmp_path: Path, scenario: str
) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert workflow["concurrency"]["cancel-in-progress"] is False
    job = workflow["jobs"]["deploy"]
    assert job["if"] == "github.ref == 'refs/heads/main'"
    verify, deploy = job["steps"]
    assert "PORTAINER_WEBHOOK_URL" not in verify.get("env", {})
    assert "${{ inputs." not in verify["run"]
    run = {
        "id": 123, "run_attempt": 2, "path": ".github/workflows/publish-devel.yml",
        "head_branch": "main", "status": "completed", "conclusion": "success",
        "head_sha": "a" * 40,
    }
    if scenario == "failed":
        run["conclusion"] = "failure"
    elif scenario == "in-progress":
        run["status"] = "in_progress"
    elif scenario == "wrong-workflow":
        run["path"] = ".github/workflows/publish-images.yml"
    elif scenario == "branch":
        run["head_branch"] = "fix/not-production"
    run_json = tmp_path / "run.json"
    run_json.write_text(json.dumps(run))
    gh = tmp_path / "gh"
    gh.write_text('#!/bin/sh\ncat "$RUN_JSON"\n')
    gh.chmod(0o755)
    curl = tmp_path / "curl"
    curl.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" > "$WEBHOOK_LOG"\n'
        'if [ "$SCENARIO" = webhook-failure ]; then exit 22; fi\n'
    )
    curl.chmod(0o755)
    webhook_log = tmp_path / "webhook.log"
    summary = tmp_path / "summary"
    tag = "devel-" + "a" * 40 + "-123-2"
    if scenario == "wrong-tag":
        tag = "devel-unpublished"
    elif scenario == "wrong-attempt":
        tag = "devel-" + "a" * 40 + "-123-1"
    result = subprocess.run(
        ["bash", "-c", verify["run"] + "\n" + deploy["run"]],
        cwd=tmp_path, capture_output=True, text=True, timeout=15,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "SCENARIO": scenario, "RUN_JSON": str(run_json), "WEBHOOK_LOG": str(webhook_log),
             "GITHUB_REPOSITORY": "example/aax", "GITHUB_STEP_SUMMARY": str(summary),
             "BUNDLE_RUN_ID": "invalid" if scenario == "invalid-id" else "123",
             "BUNDLE_TAG": tag,
             "PORTAINER_PINS_CONFIRMED": "false" if scenario == "unconfirmed" else "true",
             "PORTAINER_WEBHOOK_URL": "" if scenario == "missing-webhook" else "https://portainer.invalid/webhook"},
    )
    assert (result.returncode == 0) == (scenario == "valid"), result.stderr
    assert webhook_log.exists() == (scenario in ("valid", "webhook-failure"))
    assert summary.exists() == (scenario == "valid")
    if scenario == "valid":
        assert "Verify service health and activations" in summary.read_text()
