"""
Tests for Kubernetes deployment configuration and topology.

Static manifest rendering checks run whenever kubectl is installed.
Runtime cluster checks run only when kubectl can reach a cluster.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def kubectl_installed() -> bool:
    """Check if kubectl is installed."""
    return shutil.which("kubectl") is not None


def kubectl_cluster_available() -> bool:
    """Check if kubectl can connect to a cluster."""
    if not kubectl_installed():
        return False
    result = subprocess.run(
        ["kubectl", "cluster-info"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.returncode == 0


def render_kustomize(path: str = "k8s/") -> str:
    """Render Kubernetes manifests with kustomize for the given path."""
    result = subprocess.run(
        ["kubectl", "kustomize", "--load-restrictor=LoadRestrictionsNone", path],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Invalid kustomize config for {path}: {result.stderr}"
    return result.stdout


def _manifest_doc(rendered_manifests: str, kind: str, name: str) -> str:
    """Return one rendered manifest document for a given kind/name."""
    marker_kind = f"kind: {kind}"
    marker_name = f"name: {name}"
    for doc in rendered_manifests.split("\n---\n"):
        if marker_kind in doc and marker_name in doc:
            return doc
    return ""


@pytest.fixture(scope="module")
def rendered_manifests() -> str:
    """Return the rendered kustomize output."""
    if not kubectl_installed():
        pytest.skip("kubectl not installed")
    return render_kustomize()


@pytest.fixture(scope="module")
def rendered_ha_manifests() -> str:
    """Return rendered kustomize output for optional HA overlay."""
    if not kubectl_installed():
        pytest.skip("kubectl not installed")
    return render_kustomize("k8s/overlays/ha")


@pytest.fixture(scope="module")
def k8s_deployed() -> Any:
    """Deploy to Kubernetes before runtime tests and clean up after."""
    if not kubectl_cluster_available():
        pytest.skip("kubectl not available or no Kubernetes cluster configured")

    result = subprocess.run(
        ["kubectl", "apply", "-k", "k8s/"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Failed to deploy: {result.stderr}"

    yield

    subprocess.run(
        ["kubectl", "delete", "namespace", "aax"],
        capture_output=True,
        cwd=str(REPO_ROOT),
    )


class TestKubernetesManifestRendering:
    """Static validation for rendered Kubernetes manifests."""

    def test_kustomize_config_valid(self, rendered_manifests: str) -> None:
        """Test that kustomize renders the full stack."""
        assert "kind: Namespace" in rendered_manifests
        assert "name: aax" in rendered_manifests

    def test_full_stack_deployments_rendered(self, rendered_manifests: str) -> None:
        """Test that all major platform deployments are present in rendered manifests."""
        expected_deployments = [
            "name: ee-base",
            "name: ee-builder",
            "name: dev-tools",
            "name: awx-postgres",
            "name: awx-redis",
            "name: awx-web",
            "name: awx-task",
            "name: awx-receptor",
            "name: receptor-hop",
            "name: receptor-execution",
            "name: hub-postgres",
            "name: hub-redis",
            "name: pulp-api",
            "name: pulp-content",
            "name: pulp-worker",
            "name: galaxy-ng",
            "name: eda-postgres",
            "name: eda-redis",
            "name: eda-controller",
            "name: gateway",
        ]
        for deployment in expected_deployments:
            assert deployment in rendered_manifests

    def test_full_stack_services_rendered(self, rendered_manifests: str) -> None:
        """Test that the service layer for the full stack is present."""
        expected_services = [
            "name: ee-base",
            "name: ee-builder",
            "name: dev-tools",
            "name: awx-postgres",
            "name: awx-redis",
            "name: awx-web",
            "name: awx-receptor",
            "name: receptor-hop",
            "name: receptor-execution",
            "name: hub-postgres",
            "name: hub-redis",
            "name: pulp-api",
            "name: pulp-content",
            "name: galaxy-ng",
            "name: eda-postgres",
            "name: eda-redis",
            "name: eda-controller",
            "name: gateway",
        ]
        for service in expected_services:
            assert service in rendered_manifests

    def test_receptor_mesh_configs_rendered(self, rendered_manifests: str) -> None:
        """Test that the controller, hop, and execution Receptor configs are rendered."""
        assert "id: receptor-controller" in rendered_manifests
        assert "id: receptor-hop" in rendered_manifests
        assert "id: receptor-execution" in rendered_manifests
        assert "address: receptor-hop:8888" in rendered_manifests
        assert "address: awx-receptor:8888" in rendered_manifests
        assert "address: receptor-execution:8888" in rendered_manifests
        assert "worktype: ansible-runner" in rendered_manifests

    def test_full_stack_storage_rendered(self, rendered_manifests: str) -> None:
        """Test that persistent storage exists for stateful platform components."""
        expected_claims = [
            "name: workspace",
            "name: ee-builds",
            "name: ee-definitions",
            "name: dev-workspace",
            "name: awx-postgres-data",
            "name: awx-projects",
            "name: awx-rsyslog",
            "name: hub-postgres-data",
            "name: hub-pulp-storage",
            "name: hub-assets",
            "name: eda-postgres-data",
            "name: eda-projects",
            "name: eda-logs",
        ]
        for claim in expected_claims:
            assert claim in rendered_manifests


class TestKubernetesHAOverlay:
    """Static validation for the optional HA overlay."""

    def test_ha_overlay_renders(self, rendered_ha_manifests: str) -> None:
        """HA overlay should render cleanly via kustomize."""
        assert "kind: Deployment" in rendered_ha_manifests
        assert "kind: PodDisruptionBudget" in rendered_ha_manifests

    def test_ha_overlay_scales_key_deployments(self, rendered_ha_manifests: str) -> None:
        """HA overlay should set multi-replica counts for key control-plane deployments."""
        scaled_deployments = [
            "awx-web",
            "awx-task",
            "galaxy-ng",
            "pulp-api",
            "pulp-content",
            "eda-controller",
            "gateway",
        ]
        for deployment in scaled_deployments:
            doc = _manifest_doc(rendered_ha_manifests, "Deployment", deployment)
            assert doc, f"Missing Deployment manifest for {deployment}"
            assert "replicas: 2" in doc

    def test_ha_overlay_defines_disruption_budgets(self, rendered_ha_manifests: str) -> None:
        """HA overlay should include PodDisruptionBudgets for key edge/control services."""
        expected_pdbs = [
            "awx-web-pdb",
            "galaxy-ng-pdb",
            "gateway-pdb",
            "eda-controller-pdb",
        ]
        for pdb in expected_pdbs:
            doc = _manifest_doc(rendered_ha_manifests, "PodDisruptionBudget", pdb)
            assert doc, f"Missing PodDisruptionBudget for {pdb}"
            assert "minAvailable: 1" in doc


@pytest.mark.skipif(
    not kubectl_cluster_available(),
    reason="kubectl not available or no Kubernetes cluster configured",
)
class TestKubernetesRuntime:
    """Runtime checks for the deployed Kubernetes resources."""

    def test_expected_deployments_exist(self, k8s_deployed: Any) -> None:
        """Test that the key deployments exist after apply."""
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", "aax", "-o", "name"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        deployments = result.stdout.strip().split("\n")
        expected = [
            "deployment.apps/awx-web",
            "deployment.apps/awx-task",
            "deployment.apps/awx-receptor",
            "deployment.apps/receptor-hop",
            "deployment.apps/receptor-execution",
            "deployment.apps/galaxy-ng",
            "deployment.apps/pulp-api",
            "deployment.apps/pulp-content",
            "deployment.apps/pulp-worker",
            "deployment.apps/eda-controller",
            "deployment.apps/gateway",
        ]
        for deployment in expected:
            assert deployment in deployments

    def test_expected_services_exist(self, k8s_deployed: Any) -> None:
        """Test that the key services exist after apply."""
        result = subprocess.run(
            ["kubectl", "get", "services", "-n", "aax", "-o", "name"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        services = result.stdout.strip().split("\n")
        expected = [
            "service/awx-web",
            "service/awx-receptor",
            "service/receptor-hop",
            "service/receptor-execution",
            "service/galaxy-ng",
            "service/pulp-api",
            "service/pulp-content",
            "service/eda-controller",
            "service/gateway",
        ]
        for service in expected:
            assert service in services

    def test_gateway_service_has_cluster_ip(self, k8s_deployed: Any) -> None:
        """Test that the gateway service is reachable inside the cluster."""
        result = subprocess.run(
            ["kubectl", "get", "service", "gateway", "-n", "aax", "-o", "jsonpath={.spec.clusterIP}"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() not in ("", "None")
