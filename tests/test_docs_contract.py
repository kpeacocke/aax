"""Docs/runtime contract checks to detect drift in critical operator guidance."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_env_doc_mentions_dev_cookie_override() -> None:
    """Environment docs should describe the explicit dev cookie override flag."""
    content = _read("docs/ENVIRONMENT_VARIABLES.md")
    assert "AWX_ALLOW_INSECURE_COOKIES" in content


def test_workflow_docs_do_not_claim_latest_pushes() -> None:
    """Workflow docs should match version-only image publishing policy."""
    content = _read(".github/workflows/README.md")
    assert "aax-*:latest" not in content
    assert "aax-IMAGE:latest" not in content


def test_hub_docs_use_gateway_for_pulp_endpoints() -> None:
    """Hub docs should reference gateway endpoints for Pulp access."""
    content = _read("hub/HUB.md")
    assert "http://localhost:8088/pulp/api/v3/" in content
    assert "http://localhost:8088/pulp/content/" in content


def test_env_example_documents_cookie_override_flag() -> None:
    """The operator env template should include the explicit dev cookie override flag."""
    content = _read(".env.example")
    assert "AWX_ALLOW_INSECURE_COOKIES=false" in content


def test_faq_documents_ssh_secure_default_opt_out_guidance() -> None:
    """FAQ should document local-lab opt-out while preserving secure SSH default guidance."""
    content = _read("docs/FAQ.md")
    assert "host_key_checking=True" in content
    assert "ANSIBLE_HOST_KEY_CHECKING=False" in content


def test_canonical_endpoints_doc_exists_and_covers_defaults() -> None:
    """Canonical endpoints documentation should define current default profile endpoints."""
    content = _read("docs/ENDPOINTS.md")
    required_tokens = [
        "HOST_BIND=127.0.0.1",
        "AWX_WEB_PORT",
        "AWX_RECEPTOR_PORT",
        "GATEWAY_PORT",
        "GALAXY_PORT",
        "EDA_PORT",
        "http://localhost:8088/pulp/api/v3/",
    ]
    for token in required_tokens:
        assert token in content


def test_security_baseline_doc_defines_dev_and_production_like_modes() -> None:
    """Security baseline docs should define controls for dev and production-like operation."""
    content = _read("docs/SECURITY_BASELINE.md")
    required_tokens = [
        "Local-Dev Baseline",
        "Production-Like Baseline",
        "AWX_ALLOW_INSECURE_COOKIES",
        "HOST_BIND",
        "tests/test_repo_policy.py",
        "tests/test_docs_contract.py",
    ]
    for token in required_tokens:
        assert token in content


def test_production_secret_management_doc_and_overlay_exist() -> None:
    """Production secret guidance should include an ExternalSecret overlay path."""
    content = _read("docs/SECRETS_PRODUCTION.md")
    required_tokens = [
        "k8s/overlays/production",
        "external-secret.example.yaml",
        "kubectl apply -k k8s/overlays/production",
    ]
    for token in required_tokens:
        assert token in content


def test_privilege_model_doc_tracks_root_and_socket_surface() -> None:
    """Privilege model docs should enumerate root services and docker socket scope."""
    content = _read("docs/PRIVILEGE_MODEL.md")
    required_tokens = [
        "awx-web",
        "awx-task",
        "awx-receptor",
        "ee-builder",
        "/var/run/docker.sock",
    ]
    for token in required_tokens:
        assert token in content


def test_version_matrix_doc_exists_with_pinned_defaults() -> None:
    """Version matrix docs should define current pinned default tags."""
    content = _read("docs/VERSION_MATRIX.md")
    required_tokens = [
        "awx",
        "ee-base",
        "ee-builder",
        "dev-tools",
        "galaxy-ng",
        "pulp",
        "eda-controller",
        "gateway",
        "1.0.0",
        "1.5.7",
    ]
    for token in required_tokens:
        assert token in content


def test_network_boundaries_doc_and_debug_exposure_override_exist() -> None:
    """Network boundary docs should define gateway-first defaults and debug-only override path."""
    boundaries = _read("docs/NETWORK_BOUNDARIES.md")
    override = _read("docker-compose.debug-exposure.yml")

    for token in ["Gateway-first", "HOST_BIND=127.0.0.1", "docker-compose.debug-exposure.yml"]:
        assert token in boundaries

    for token in [
        "0.0.0.0:${AWX_WEB_PORT:-8080}:8052",
        "0.0.0.0:${GATEWAY_PORT:-8088}:8080",
        "0.0.0.0:${EDA_PORT:-5000}:5000",
    ]:
        assert token in override


def test_ha_docs_map_claims_to_overlay_and_plan() -> None:
    """HA docs should reference the implemented overlay and explicit not-yet-implemented scope."""
    deployment_guide = _read("docs/HA-DEPLOYMENT.md")
    milestone_plan = _read("docs/HA_MILESTONE_PLAN.md")

    for token in [
        "Current Implementation Status",
        "k8s/overlays/ha",
        "Not yet implemented",
        "PostgreSQL replication/failover topology",
        "Redis Sentinel",
    ]:
        assert token in deployment_guide

    for token in [
        "Milestone 1: Control-plane replica resilience (implemented)",
        "Milestone 2: Stateful dependency HA (planned)",
        "Milestone 3: Shared storage and failover validation (planned)",
        "kubectl apply -k k8s/overlays/ha",
    ]:
        assert token in milestone_plan
