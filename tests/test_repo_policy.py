"""Repository policy checks for deployment defaults and security baselines."""

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _compose_env_var_names(compose_text: str) -> set[str]:
    """Return all ${VAR...} interpolation names used in compose."""
    return set(re.findall(r"\$\{([A-Z0-9_]+)(?::[-?][^}]*)?\}", compose_text))


def _env_example_var_names(env_example_text: str) -> set[str]:
    """Return all KEY names declared in .env.example."""
    return set(re.findall(r"^([A-Z0-9_]+)=.*$", env_example_text, flags=re.MULTILINE))


def test_kubernetes_manifests_do_not_use_latest_tags() -> None:
    """Deployment manifests should be pinned to tested image tags."""
    k8s_files = list((REPO_ROOT / "k8s").glob("*.yaml"))
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


def test_release_workflow_has_secret_scan_gate() -> None:
    """Release workflow should run a blocking secret scan before release gates."""
    content = _read(".github/workflows/release.yml")
    required_tokens = [
        "secrets-scan:",
        "name: Scan for Secrets",
        "gitleaks/gitleaks-action@v2",
        "needs: [secrets-scan]",
        "needs: [test, security-scan, secrets-scan]",
    ]
    for token in required_tokens:
        assert token in content


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
    """Runtime entrypoints and compose config should not ship weak secret fallbacks."""
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


def test_kubernetes_hub_allowed_hosts_are_not_wildcard() -> None:
    """Galaxy should not allow all hosts by default in shipped manifests."""
    content = _read("k8s/hub-stack.yaml")
    assert 'value: "*"' not in content


def test_awx_task_has_no_docker_socket_mount_in_k8s() -> None:
    """Kubernetes AWX task deployment should not mount the host Docker socket."""
    content = _read("k8s/controller-stack.yaml")
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
        '${HOST_BIND:-127.0.0.1}:${AWX_WEB_PORT:-8080}:8052',
        '${HOST_BIND:-127.0.0.1}:${AWX_RECEPTOR_PORT:-8888}:8888',
        '${HOST_BIND:-127.0.0.1}:${GATEWAY_PORT:-8088}:8080',
        '${HOST_BIND:-127.0.0.1}:${GALAXY_PORT:-5001}:8000',
        '${HOST_BIND:-127.0.0.1}:${EDA_PORT:-5000}:5000',
    ]
    for binding in required_bindings:
        assert binding in content


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
        "awx-receptor",
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


def test_docker_socket_mount_is_restricted_to_ee_builder() -> None:
    """Docker socket mount should be isolated to ee-builder in compose."""
    content = _read("docker-compose.yml")
    socket_services = _compose_services_with_exact_setting(
        content, "- /var/run/docker.sock:/var/run/docker.sock"
    )
    assert socket_services == {"ee-builder"}


def test_hub_and_pulp_compose_secrets_are_required() -> None:
    """Hub and Pulp runtime secrets should fail fast when missing."""
    content = _read("docker-compose.yml")
    required_tokens = [
        "${HUB_DB_PASSWORD:?HUB_DB_PASSWORD must be set",
        "${HUB_ADMIN_PASSWORD:?HUB_ADMIN_PASSWORD must be set",
        "${GALAXY_SECRET_KEY:?GALAXY_SECRET_KEY must be set",
        '"${PULP_SECRET_KEY:?PULP_SECRET_KEY must be set',
    ]
    for token in required_tokens:
        assert token in content


def test_placeholder_secret_tokens_are_confined_to_templates() -> None:
    """Placeholder secret marker values should stay in template files only."""
    allowed_files = {
        ".env.example",
        "k8s/secret.yaml",
        "k8s/awx-settings-configmap.yaml",
        "k8s/overlays/production/external-secret.example.yaml",
    }
    marker_tokens = ["REPLACE_WITH_", "CHANGE_ME_"]

    offenders: list[str] = []
    for file_path in REPO_ROOT.rglob("*.yaml"):
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
    compose_vars = _compose_env_var_names(_read("docker-compose.yml"))
    env_example_vars = _env_example_var_names(_read(".env.example"))

    missing_in_env_example = sorted(compose_vars - env_example_vars)
    unused_in_env_example = sorted(env_example_vars - compose_vars)

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
