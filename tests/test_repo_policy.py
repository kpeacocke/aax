"""Repository policy checks for deployment defaults and security baselines."""

from pathlib import Path
import json
import os
import re
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _reconcile_audit(
    tmp_path: Path, audit: object, status: str, issues: list[dict],
    direct_audit: object | None = None, direct_status: str | None = None,
    ref: str = "refs/heads/main",
) -> dict:
    (tmp_path / "audit-results.json").write_text(json.dumps(audit))
    (tmp_path / "audit-direct-results.json").write_text(
        json.dumps(audit if direct_audit is None else direct_audit)
    )
    for image in ("ee-base", "ee-builder", "dev-tools"):
        directory = tmp_path / "images" / image
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "requirements.txt").write_text("package==1.0\n")
    script = REPO_ROOT / ".github/scripts/reconcile-dependency-audit.cjs"
    harness = r"""
const reconcile = require(process.argv[1]);
const calls = [];
const output = {};
const issues = JSON.parse(process.env.TEST_ISSUES);
const github = {
  paginate: async (_method, params) => { calls.push(['list', params]); return issues; },
  rest: { issues: {
    listForRepo: () => {},
    update: async params => { calls.push(['update', params]); },
    create: async params => { calls.push(['create', params]); return {data: {number: 123}}; },
    createComment: async params => { calls.push(['comment', params]); }
  }}
};
const context = {
  repo: {owner: 'owner', repo: 'repo'}, sha: 'verified-commit',
  serverUrl: 'https://github.com', runId: 456, ref: process.env.TEST_REF
};
reconcile({github, context, core: {setOutput: (key, value) => {output[key] = value;}}})
  .then(() => console.log(JSON.stringify({calls, output})))
  .catch(error => {
    console.log(JSON.stringify({calls, output, error: error.message}));
    process.exitCode = 1;
  });
"""
    result = subprocess.run(
        ["node", "-e", harness, str(script)],
        cwd=tmp_path,
        env={
            **os.environ, "AUDIT_EXIT_STATUS": status, "TEST_ISSUES": json.dumps(issues),
            "AUDIT_DIRECT_EXIT_STATUS": status if direct_status is None else direct_status,
            "TEST_REF": ref,
        },
        capture_output=True, text=True, timeout=30,
    )
    parsed = json.loads(result.stdout)
    assert result.returncode == (1 if "error" in parsed else 0), result.stderr
    return parsed


@pytest.mark.parametrize("status,vulns", [
    ("0", []),
    ("1", [{"id": "CVE-test", "fix_versions": ["2.0"]}]),
])
def test_dependency_issue_lifecycle(tmp_path: Path, status: str, vulns: list[dict]) -> None:
    title = "\U0001f512 Security: Vulnerable dependencies detected"
    issues = [
        {"number": 2, "title": title},
        {"number": 9, "title": title},
        {"number": 3, "title": "Unrelated security issue"},
        {"number": 4, "title": title, "pull_request": {"url": "not-an-issue"}},
    ]
    audit = {"dependencies": [{"name": "package", "version": "1.0", "vulns": vulns}]}
    result = _reconcile_audit(tmp_path, audit, status, issues)
    assert result["output"] == {"vulnerabilities": str(status == "1").lower()}
    updates = [call[1] for call in result["calls"] if call[0] == "update"]
    assert {update["issue_number"] for update in updates} == {2, 9}
    assert not any(call[0] == "create" for call in result["calls"])
    comments = [call[1] for call in result["calls"] if call[0] == "comment"]
    if status == "0":
        assert all(update["state_reason"] == "completed" for update in updates)
        assert all("actions/runs/456" in comment["body"] for comment in comments)
        assert all("does not certify other" in comment["body"] for comment in comments)
    else:
        canonical = next(update for update in updates if update["issue_number"] == 9)
        assert "CVE-test" in canonical["body"] and "workflow remains failing" in canonical["body"]
        duplicate = next(update for update in updates if update["issue_number"] == 2)
        assert duplicate["state_reason"] == "not_planned"
        assert comments[0]["issue_number"] == 2 and "#9" in comments[0]["body"]


def test_dependency_issue_created_only_for_genuine_findings(tmp_path: Path) -> None:
    audit = {"dependencies": [{"name": "package", "version": "1.0", "vulns": []}]}
    clean = _reconcile_audit(tmp_path, audit, "0", [])
    assert [call[0] for call in clean["calls"]] == ["list"]
    audit["dependencies"][0]["vulns"] = [{"id": "CVE-test", "fix_versions": []}]
    vulnerable = _reconcile_audit(tmp_path, audit, "1", [])
    assert [call[0] for call in vulnerable["calls"]] == ["list", "create"]
    assert vulnerable["output"]["vulnerabilities"] == "true"


@pytest.mark.parametrize("status,vulns", [
    ("0", []),
    ("1", [{"id": "CVE-test", "fix_versions": []}]),
])
def test_branch_audits_cannot_mutate_main_dependency_issues(
    tmp_path: Path, status: str, vulns: list[dict],
) -> None:
    audit = {"dependencies": [{"name": "package", "version": "1.0", "vulns": vulns}]}
    result = _reconcile_audit(tmp_path, audit, status, [], ref="refs/heads/fix/example")
    assert result["calls"] == []
    assert result["output"] == {"vulnerabilities": str(status == "1").lower()}


def test_direct_pin_findings_are_not_lost_by_resolver_audit(tmp_path: Path) -> None:
    resolved = {"dependencies": [{"name": "transitive", "version": "1", "vulns": []}]}
    direct = {"dependencies": [{"name": "package", "version": "1.0", "vulns": [
        {"id": "CVE-bootstrap", "fix_versions": ["2.0"]}
    ]}]}
    result = _reconcile_audit(tmp_path, resolved, "0", [], direct, "1")
    assert result["output"]["vulnerabilities"] == "true"
    created = next(call[1] for call in result["calls"] if call[0] == "create")
    assert "CVE-bootstrap" in created["body"]


def test_incomplete_direct_pin_inventory_cannot_close_issues(tmp_path: Path) -> None:
    incomplete = {"dependencies": [{"name": "transitive", "version": "1", "vulns": []}]}
    result = _reconcile_audit(tmp_path, incomplete, "0", [])
    assert "omitted required pin package==1.0" in result["error"]
    assert result["calls"] == [] and result["output"] == {}


@pytest.mark.parametrize("audit,status", [
    ({}, "0"),
    ({"dependencies": []}, "0"),
    ({"dependencies": [{"name": "p", "version": "1"}]}, "0"),
    ({"dependencies": [{"name": "p", "version": "1", "vulns": [], "skip_reason": "offline"}]}, "0"),
    ({"dependencies": [{"name": "p", "version": "1", "vulns": [{"id": "CVE-test"}]}]}, "1"),
    ({"dependencies": [{"name": "p", "version": "1", "vulns": []}]}, "1"),
    ({"dependencies": [{"name": "p", "version": "1", "vulns": []}]}, "2"),
    ({"dependencies": [{"name": "p", "version": "1", "vulns": []}]}, ""),
    ({"dependencies": [{"name": "p", "version": "1", "vulns": [
        {"id": "CVE-test", "fix_versions": ["2"]}
    ]}]}, "0"),
])
def test_invalid_audits_cannot_close_issues(tmp_path: Path, audit: object, status: str) -> None:
    result = _reconcile_audit(tmp_path, audit, status, [])
    assert "error" in result
    assert result["calls"] == []
    assert result["output"] == {}


def test_dependency_workflow_validates_before_reporting_and_retains_failure_gate() -> None:
    content = _read(".github/workflows/dependencies.yml")
    assert "reconcile-dependency-audit.cjs" in content
    assert "AUDIT_EXIT_STATUS: ${{ steps.audit-command.outputs.status }}" in content
    assert "AUDIT_DIRECT_EXIT_STATUS: ${{ steps.audit-command.outputs.direct-status }}" in content
    assert "--disable-pip --no-deps" in content and "audit-direct-results.json" in content
    assert "if: steps.audit.outputs.vulnerabilities == 'true'\n        run: exit 1" in content
    assert "if: always()" in content and "name: dependency-audit" in content
    assert "group: dependency-management-${{ github.ref }}" in content


def _compose_env_var_names(compose_text: str) -> set[str]:
    """Return all ${VAR...} interpolation names used in compose."""
    return set(re.findall(r"\$\{([A-Z0-9_]+)(?::[-?][^}]*)?\}", compose_text.replace("$$", "")))


def test_compose_interpolation_excludes_escaped_container_variables() -> None:
    assert _compose_env_var_names("${HOST} $${CONTAINER:-false} $$${OTHER_HOST}") == {
        "HOST", "OTHER_HOST",
    }


def _env_example_var_names(env_example_text: str) -> set[str]:
    """Return all KEY names declared in .env.example."""
    return set(re.findall(r"^([A-Z0-9_]+)=.*$", env_example_text, flags=re.MULTILINE))


def test_kubernetes_manifests_do_not_use_latest_tags() -> None:
    """Deployment manifests should be pinned to tested image tags."""
    k8s_dir = REPO_ROOT / "k8s"
    k8s_files = list(k8s_dir.rglob("*.yaml")) + list(k8s_dir.rglob("*.yml"))
    offenders = []
    for file_path in k8s_files:
        content = file_path.read_text(encoding="utf-8")
        if ":latest" in content:
            offenders.append(file_path.relative_to(REPO_ROOT).as_posix())
    assert offenders == [], f"Found unpinned latest tags in: {', '.join(offenders)}"


def test_release_workflow_does_not_publish_latest_tags() -> None:
    """Release workflow should publish versioned images only."""
    content = _read(".github/workflows/release.yml")
    assert ":latest" not in content


def test_compose_main_channel_defaults_match_published_images() -> None:
    """Compose defaults must resolve to tags published by the main workflow."""
    compose = _read("docker-compose.yml")
    env_example = _read(".env.example")
    publish_workflow = _read(".github/workflows/publish-images.yml")

    assert "${AAX_VERSION:-1.0.0}" not in compose
    assert "${AAX_VERSION:-latest}" in compose
    assert "AAX_VERSION=latest" in env_example
    assert "type=raw,value=latest" in publish_workflow


def test_gateway_uses_supported_nginx_patch_channel() -> None:
    """Gateway should follow a maintained nginx minor channel, not an EOL one."""
    dockerfile = _read("images/gateway/Dockerfile")
    assert "ARG NGINX_VERSION=1.30-alpine" in dockerfile
    assert "FROM nginx:${NGINX_VERSION}" in dockerfile
    assert "nginx:1.27-alpine" not in dockerfile


def test_release_workflow_has_secret_scan_gate() -> None:
    """Release workflow should run a blocking secret scan before release gates."""
    content = _read(".github/workflows/release.yml")
    required_tokens = [
        "secrets-scan:",
        "name: Scan for Secrets",
        "gitleaks/gitleaks-action@",
        "needs: [secrets-scan]",
        "needs: [test, security-scan, secrets-scan]",
    ]
    for token in required_tokens:
        assert token in content


def test_release_gate_blocks_fixable_high_and_critical_vulnerabilities() -> None:
    """Unfixed findings remain reported; fixable high/critical findings block release."""
    content = _read(".github/workflows/release.yml")
    report_match = re.search(
        r"      - name: Run Trivy vulnerability scanner\n.*?(?=\n      - name:)",
        content,
        flags=re.DOTALL,
    )
    gate_match = re.search(
        r"      - name: Gate on fixable high and critical vulnerabilities\n.*?(?=\n      - name:)",
        content,
        flags=re.DOTALL,
    )
    assert report_match is not None
    assert gate_match is not None
    report_step = report_match.group(0)
    gate_step = gate_match.group(0)

    assert "format: sarif" in report_step
    assert "ignore-unfixed: true" not in report_step
    assert "format: table" in gate_step
    assert "severity: HIGH,CRITICAL" in gate_step
    assert "ignore-unfixed: true" in gate_step
    assert "exit-code: 1" in gate_step


def test_ci_workflow_does_not_use_latest_image_tags() -> None:
    """CI workflow should build and scan pinned image tags only."""
    content = _read(".github/workflows/ci.yml")
    disallowed_tokens = [
        "aax/ee-base:latest",
        "BASE_IMAGE=aax/ee-base:latest",
        "aax/${{ matrix.image }}:latest",
        "image-ref: aax/${{ matrix.image }}:latest",
        "image: aax/${{ matrix.image }}:latest",
    ]
    offenders = [token for token in disallowed_tokens if token in content]
    assert offenders == [], "Found unpinned latest tags in CI workflow:\n" + "\n".join(offenders)


def test_runtime_files_do_not_contain_weak_secret_fallbacks() -> None:
    """Maintained runtime and Kubernetes config must not add weak secret fallbacks."""
    checks = {
        "docker-compose.yml": [
            ":-password}",
            ":-awxpass}",
            ":-hubpassword}",
            ":-edapass}",
            ":-changeme}",
            ":-change-me-to-a-long-random-string}",
            "SESSION_COOKIE_SECURE = False",
            "CSRF_COOKIE_SECURE = False",
            "AWX_SESSION_COOKIE_SECURE:",
            "AWX_CSRF_COOKIE_SECURE:",
        ],
        "images/awx/entrypoint-web.sh": [
            "AWX_ADMIN_PASSWORD:-password",
        ],
        "images/awx/setup-and-run.sh": [
            "os.getenv('DATABASE_PASSWORD', 'awxpass')",
            "os.getenv('SECRET_KEY', 'awxsecret')",
            "BROADCAST_WEBSOCKET_SECRET = os.getenv('SECRET_KEY', 'awxsecret')",
        ],
        "k8s/awx-settings-configmap.yaml": [
            "awxsecret_change_me",
            "awxpass",
            "SESSION_COOKIE_SECURE = False",
            "CSRF_COOKIE_SECURE = False",
        ],
    }

    failures = []
    for relative_path, disallowed_tokens in checks.items():
        content = _read(relative_path)
        for token in disallowed_tokens:
            if token in content:
                failures.append(f"{relative_path}: {token}")

    assert failures == [], "Weak runtime defaults remain:\n" + "\n".join(failures)
    assert "CHANGE_ME_PULP_SECRET_KEY" not in _read("images/galaxy-runtime/entrypoint.py")
    assert "key: PULP_SECRET_KEY" in _read("k8s/hub-stack.yaml")
    assert "key: SECRET_KEY" in _read("k8s/eda-stack.yaml")


def test_kubernetes_hub_allowed_hosts_are_not_wildcard() -> None:
    """Galaxy should not allow all hosts by default in shipped manifests."""
    content = _read("k8s/hub-stack.yaml")
    assert 'value: "*"' not in content


def test_awx_task_has_no_docker_socket_mount_in_k8s() -> None:
    """Kubernetes AWX task deployment should not mount the host Docker socket."""
    content = _read("k8s/controller-stack.yaml")
    assert "name: awx-task" in content
    assert "name: awx-receptor" in content
    awx_task_section = content.split("name: awx-task", 1)[1].split("name: awx-receptor", 1)[0]
    assert "/var/run/docker.sock" not in awx_task_section


def test_env_example_defaults_host_bind_to_localhost() -> None:
    """Environment defaults should bind published ports to localhost."""
    content = _read(".env.example")
    assert "HOST_BIND=127.0.0.1" in content
    assert "HOST_BIND=0.0.0.0" not in content


def test_compose_published_ports_use_localhost_host_bind_default() -> None:
    """Compose published ports should use HOST_BIND with localhost default."""
    content = _read("docker-compose.yml")
    required_bindings = [
        '"${HOST_BIND:-127.0.0.1}:${AWX_WEB_PORT:-18080}:8052"',
        '"${HOST_BIND:-127.0.0.1}:${GATEWAY_PORT:-18088}:8080"',
        '"${HOST_BIND:-127.0.0.1}:${GALAXY_PORT:-15001}:8000"',
        '"${HOST_BIND:-127.0.0.1}:${EDA_PORT:-15000}:5000"',
    ]
    for binding in required_bindings:
        assert binding in content


def test_devel_overlay_supports_registry_tagged_images() -> None:
    """Portainer can select immutable GHCR devel images through environment variables."""
    overlay = _read("docker-compose.devel.yml")
    script = _read("scripts/deploy-devel.sh")
    expected_images = [
        "${DEVEL_GATEWAY_IMAGE:-ghcr.io/kpeacocke/aax-gateway}:${DEVEL_IMAGE_TAG:-devel}",
        "${DEVEL_PULP_IMAGE:-ghcr.io/kpeacocke/aax-pulp}:${DEVEL_IMAGE_TAG:-devel}",
        "${DEVEL_GALAXY_IMAGE:-ghcr.io/kpeacocke/aax-galaxy-ng}:${DEVEL_IMAGE_TAG:-devel}",
    ]
    for image in expected_images:
        assert image in overlay
    assert "DEVEL_IMAGE_TAG" in script


def test_devel_publish_workflow_publishes_immutable_bundle() -> None:
    """The devel workflow must publish every image needed by the overlay."""
    workflow = _read(".github/workflows/publish-devel.yml")
    assert re.search(r"uses: docker/login-action@[0-9a-f]{40}(?:\s|$)", workflow)
    scripts = "\n".join(_read(path) for path in [
        "scripts/build-bundle-image.sh", "scripts/promote-bundle.sh",
        "scripts/bundle-candidate.sh",
    ])
    required = [
        "packages: write",
        "devel-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}",
        "SETUPTOOLS_SCM_PRETEND_VERSION=",
        "Record exact build sources",
        "git -C",
        "rev-parse HEAD",
        "Scan exact bundle images",
        "Gate on fixable high and critical bundle vulnerabilities",
        "bundle-reports/sources.json",
        "candidate-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT-$stage",
        "source=galaxy-ng",
        "--prefer-index=false",
        "docker push",
    ]
    missing = [token for token in required if token not in workflow + scripts]
    assert missing == [], "Devel publish workflow is missing: " + ", ".join(missing)


def test_upstream_checkout_does_not_apply_release_django_pin_to_devel() -> None:
    """AWX devel must retain its Django-compatible moving dependency set."""
    script = _read("scripts/build-upstream.sh")
    assert 'if [[ -z "$AWX_DAB_REF" ]]' in script
    assert 'preserving django-ansible-base ref from AWX $AWX_BRANCH' in script


def test_awx_dockerfile_pins_known_good_devel_ui_revision() -> None:
    """The AWX devel image should not float against ansible-ui main."""
    dockerfile = _read("images/awx/Dockerfile")
    assert "ARG UI_DEVEL_REVISION=b512f07205f2be38d29dc245e955e66e64248ae3" in dockerfile
    assert "make -C /awx/awx/ui UI_LOCAL=/ansible-ui ui" in dockerfile
    assert "UI_GIT_REPO=https://github.com/ansible/ansible-ui.git make -C /awx/awx/ui ui" not in dockerfile


def test_awx_dockerfile_preserves_24_6_1_ui_next_compatibility_path() -> None:
    """The AWX image should keep the legacy ui_next build path for 24.6.1."""
    dockerfile = _read("images/awx/Dockerfile")
    assert 'if [ "$AWX_VERSION" = "24.6.1" ]; then' in dockerfile
    assert "make -C /awx/awx/ui_next ui-next" in dockerfile


def _compose_service_port_mappings(compose_text: str) -> dict[str, list[str]]:
    """Extract published port mappings per service from docker-compose YAML text."""
    mappings: dict[str, list[str]] = {}
    current_service: str | None = None
    in_ports = False
    ports_indent = 0

    for raw_line in compose_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if indent == 2 and stripped.endswith(":") and stripped != "services:":
            current_service = stripped[:-1]
            in_ports = False
            continue

        if current_service is None:
            continue

        if stripped == "ports:":
            in_ports = True
            ports_indent = indent
            mappings.setdefault(current_service, [])
            continue

        if in_ports and stripped and indent <= ports_indent:
            in_ports = False

        if in_ports and stripped.startswith("- "):
            value = stripped[2:].strip().strip('"').strip("'")
            mappings[current_service].append(value)

    return mappings


def _compose_services_with_exact_setting(compose_text: str, setting: str) -> set[str]:
    """Return compose service names that contain a specific line token."""
    matched: set[str] = set()
    current_service: str | None = None

    for raw_line in compose_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if indent == 2 and stripped.endswith(":") and stripped != "services:":
            current_service = stripped[:-1]
            continue

        if current_service and stripped == setting:
            matched.add(current_service)

    return matched


def test_compose_only_expected_services_publish_ports() -> None:
    """Only explicitly approved edge services may publish host ports."""
    content = _read("docker-compose.yml")
    mappings = _compose_service_port_mappings(content)
    published = {service: ports for service, ports in mappings.items() if ports}

    expected_services = {
        "awx-web",
        "gateway",
        "galaxy-ng",
        "eda-controller",
    }
    assert set(published.keys()) == expected_services


def test_compose_published_ports_are_host_bind_protected() -> None:
    """All host-published ports must be bound through HOST_BIND localhost default."""
    content = _read("docker-compose.yml")
    mappings = _compose_service_port_mappings(content)
    published_ports = [port for ports in mappings.values() for port in ports]

    assert published_ports, "Expected at least one published port mapping"
    for port in published_ports:
        assert re.match(
            r"^\$\{HOST_BIND:-127\.0\.0\.1\}:\$\{[A-Z0-9_]+:-[0-9]+\}:[0-9]+$",
            port,
        ), (
            f"Unprotected published port mapping found: {port}"
        )


def test_compose_root_user_is_limited_to_known_services() -> None:
    """Only explicitly approved services should run as root in compose."""
    content = _read("docker-compose.yml")
    root_services = _compose_services_with_exact_setting(content, 'user: "0"')
    assert root_services == {
        "awx-web",
        "awx-task",
        "awx-receptor",
        "receptor-hop",
        "receptor-execution",
    }


def test_default_builders_have_no_host_docker_socket() -> None:
    for relative_path in ["docker-compose.yml", "k8s/ee-builder-deployment.yaml"]:
        assert "/var/run/docker.sock" not in _read(relative_path)
    builder = _read("k8s/ee-builder-deployment.yaml")
    assert "automountServiceAccountToken: false" in builder
    assert "hostPath:" not in builder


def test_hub_and_pulp_compose_secrets_are_required() -> None:
    """Hub and Pulp runtime secrets should fail fast when missing."""
    content = _read("docker-compose.yml")
    required_tokens = [
        "${HUB_DB_PASSWORD:?HUB_DB_PASSWORD must be set",
        "${GALAXY_SECRET_KEY:?GALAXY_SECRET_KEY must be set",
        '"${PULP_SECRET_KEY:?PULP_SECRET_KEY must be set',
    ]
    for token in required_tokens:
        assert token in content


def test_placeholder_secret_tokens_are_confined_to_templates() -> None:
    """Placeholder secret marker values should stay in template files only."""
    allowed_files = {
        ".env.example",
        "docker-compose.yml",
        "k8s/secret.yaml",
        "k8s/awx-settings-configmap.yaml",
        "k8s/overlays/production/external-secret.example.yaml",
    }
    marker_tokens = ["REPLACE_WITH_", "CHANGE_ME_"]

    offenders: list[str] = []
    yaml_files = set(REPO_ROOT.rglob("*.yaml"))
    yaml_files.update(REPO_ROOT.rglob("*.yml"))
    for file_path in sorted(yaml_files):
        rel = file_path.relative_to(REPO_ROOT).as_posix()
        content = file_path.read_text(encoding="utf-8")
        if any(token in content for token in marker_tokens) and rel not in allowed_files:
            offenders.append(rel)

    env_content = _read(".env.example")
    if not any(token in env_content for token in marker_tokens):
        offenders.append(".env.example (missing expected placeholder markers)")

    assert offenders == [], (
        "Placeholder markers found outside allowed template files:\n" + "\n".join(offenders)
    )


def test_awx_cookie_security_uses_explicit_dev_override_flag() -> None:
    """Runtime settings should only relax cookie security through explicit dev mode flag."""
    compose = _read("docker-compose.yml")
    k8s_awx_settings = _read("k8s/awx-settings-configmap.yaml")

    assert "AWX_ALLOW_INSECURE_COOKIES" in compose
    assert "AWX_ALLOW_INSECURE_COOKIES" in k8s_awx_settings
    assert "SESSION_COOKIE_SECURE = not ALLOW_INSECURE_COOKIES" in compose
    assert "CSRF_COOKIE_SECURE = not ALLOW_INSECURE_COOKIES" in compose
    assert "SESSION_COOKIE_SECURE = not ALLOW_INSECURE_COOKIES" in k8s_awx_settings
    assert "CSRF_COOKIE_SECURE = not ALLOW_INSECURE_COOKIES" in k8s_awx_settings


def test_placeholder_secret_runtime_guard_is_enabled_by_default() -> None:
    """Runtime must reject placeholder secret values unless explicit local-dev override is enabled."""
    compose = _read("docker-compose.yml")
    k8s_awx_settings = _read("k8s/awx-settings-configmap.yaml")
    env_example = _read(".env.example")
    controller_stack = _read("k8s/controller-stack.yaml")

    assert "AAX_ALLOW_PLACEHOLDER_SECRETS: ${AAX_ALLOW_PLACEHOLDER_SECRETS:-false}" in compose
    assert "ALLOW_PLACEHOLDER_SECRETS = os.getenv('AAX_ALLOW_PLACEHOLDER_SECRETS', 'false').lower() == 'true'" in compose
    assert "contains placeholder value" in compose

    assert "ALLOW_PLACEHOLDER_SECRETS" in k8s_awx_settings
    assert "AAX_ALLOW_PLACEHOLDER_SECRETS" in k8s_awx_settings
    assert "'false'" in k8s_awx_settings
    assert "== 'true'" in k8s_awx_settings
    assert "contains placeholder value" in k8s_awx_settings

    assert "AAX_ALLOW_PLACEHOLDER_SECRETS=false" in env_example
    assert "- name: AAX_ALLOW_PLACEHOLDER_SECRETS" in controller_stack


def test_eda_healthchecks_validate_dependencies() -> None:
    """EDA health checks should validate DB/Redis dependencies before reporting healthy."""
    compose = _read("docker-compose.yml")
    k8s_eda = _read("k8s/eda-stack.yaml")

    for token in [
        "EDA_DB_HOST",
        "EDA_DB_PORT",
        "EDA_REDIS_HOST",
        "EDA_REDIS_PORT",
        "urllib.request.urlopen",
        "socket.socket",
    ]:
        assert token in compose
        assert token in k8s_eda


def test_hub_static_assets_are_not_hidden_by_kubernetes_pvc() -> None:
    """Keep the legacy assets claim but use image-baked assets in Kubernetes."""
    compose = _read("docker-compose.yml")
    devel_compose = _read("docker-compose.devel.yml")
    hub_stack = _read("k8s/hub-stack.yaml")
    persistent_volumes = _read("k8s/persistent-volumes.yaml")

    assert compose.count("hub_assets:/app/static") >= 2
    assert devel_compose.count("hub_pulp_certs:/etc/pulp/certs") == 4
    for role in ("pulp-api", "pulp-content", "pulp-worker", "galaxy-ng"):
        assert f"  {role}:" in devel_compose
    assert "name: hub-assets" in persistent_volumes
    assert "hub-assets" not in hub_stack
    assert "mountPath: /app/static" not in hub_stack
    assert hub_stack.count("PULP_DB_ENCRYPTION_KEY") == 4
    assert hub_stack.count("/var/lib/pulp/db-encryption.key") == 4
    for setting in (
        "PULP_DEFAULT_FILE_STORAGE",
        "PULP_MEDIA_ROOT",
        "PULP_REDIRECT_TO_OBJECT_STORAGE",
        "PULP_SETTINGS",
    ):
        assert hub_stack.count(setting) == 4


def test_hub_admin_is_created_interactively_not_from_dead_environment() -> None:
    """The maintained Hub runtime uses its real interactive admin command."""
    hub_stack = _read("k8s/hub-stack.yaml")
    docs = _read("k8s/K8S.md")

    assert "HUB_ADMIN_PASSWORD" not in hub_stack
    assert "GALAXY_ADMIN_PASSWORD" not in hub_stack
    assert "HUB_ADMIN_PASSWORD" not in _read("k8s/secret.yaml")
    assert "django-admin createsuperuser" in docs
    assert "does not create an administrator from an" in docs
    assert "environment variable" in docs


def test_hub_manifests_use_upstream_entrypoint_commands() -> None:
    """Hub workloads dispatch through the maintained upstream entrypoint."""
    hub_stack = _read("k8s/hub-stack.yaml")

    assert 'args: ["run", "api"]' in hub_stack
    assert 'args: ["run", "content-app"]' in hub_stack
    assert 'args: ["run", "worker"]' in hub_stack


def test_gateway_routes_hub_api_paths_to_maintained_galaxy_service() -> None:
    """The gateway preserves Hub API routing without the retired WSGI wrapper."""
    gateway = _read("images/gateway/nginx.conf")

    assert "location /api/galaxy/" in gateway
    assert "location /api/automation-hub/" in gateway
    assert gateway.count("http://galaxy-ng:8000") >= 2


def test_release_workflow_records_digest_and_signing_provenance() -> None:
    """Release workflow should publish digest-level provenance with signing and SBOM attestation."""
    content = _read(".github/workflows/release.yml")
    required_tokens = [
        "steps.build-push.outputs.digest",
        "cosign sign --yes",
        "actions/attest-sbom",
        "provenance: true",
    ]
    for token in required_tokens:
        assert token in content


def test_env_example_matches_compose_variable_surface() -> None:
    """Env template and compose interpolation surface should stay synchronized."""
    compose_vars = _compose_env_var_names(
        _read("docker-compose.yml") + _read("docker-compose.devel.yml")
    )
    env_example_vars = _env_example_var_names(_read(".env.example"))
    compose_cli_only_vars = {"COMPOSE_PROFILES", "COMPOSE_PROJECT_NAME"}

    missing_in_env_example = sorted(compose_vars - env_example_vars)
    unused_in_env_example = sorted((env_example_vars - compose_vars) - compose_cli_only_vars)

    assert missing_in_env_example == [], (
        "Variables used in docker-compose.yml but missing in .env.example:\n"
        + "\n".join(missing_in_env_example)
    )
    assert unused_in_env_example == [], (
        "Variables present in .env.example but unused by docker-compose.yml:\n"
        + "\n".join(unused_in_env_example)
    )


def test_compose_hardening_controls_applied_to_hardened_services() -> None:
    """Selected runtime services should enforce no-new-privileges and cap drops."""
    content = _read("docker-compose.yml")
    no_new_priv_services = _compose_services_with_exact_setting(
        content, "- no-new-privileges:true"
    )
    cap_drop_services = _compose_services_with_exact_setting(content, "cap_drop:")
    cap_all_drop_services = _compose_services_with_exact_setting(content, "- ALL")

    expected_hardened_services = {
        "ee-base",
        "ee-builder",
        "dev-tools",
        "gateway",
        "pulp-api",
        "pulp-content",
        "pulp-worker",
        "galaxy-ng",
        "eda-controller",
    }

    assert no_new_priv_services == expected_hardened_services
    assert cap_drop_services == expected_hardened_services
    assert cap_all_drop_services == expected_hardened_services
