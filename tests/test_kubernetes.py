"""
Tests for Kubernetes deployment configuration and orchestration.
These tests verify that deployments, services, and pods work correctly in Kubernetes.

NOTE: These tests require kubectl to be installed and a Kubernetes cluster to be configured.
kubectl is installed in the dev container, but you need Docker Desktop Kubernetes or
another cluster configured and accessible.
"""
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


# Check if kubectl is available and can connect to a cluster
def kubectl_available():
    """Check if kubectl command is available and can connect to a cluster."""
    if shutil.which("kubectl") is None:
        return False
    # Check if we can connect to a cluster
    result = subprocess.run(
        ["kubectl", "cluster-info"],
        capture_output=True,
        text=True,
        timeout=5
    )
    return result.returncode == 0


# Skip all tests if kubectl is not available or no cluster is configured
pytestmark = pytest.mark.skipif(
    not kubectl_available(),
    reason="kubectl not available or no Kubernetes cluster configured"
)


@pytest.fixture(scope="module")
def k8s_deployed():
    """Deploy to Kubernetes before tests and clean up after."""
    # Apply manifests
    result = subprocess.run(
        ["kubectl", "apply", "-k", "k8s/"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    assert result.returncode == 0, f"Failed to deploy: {result.stderr}"

    # Wait for deployments to be ready
    time.sleep(15)

    yield

    # Cleanup - delete namespace
    subprocess.run(
        ["kubectl", "delete", "namespace", "aax"],
        capture_output=True,
        cwd=str(REPO_ROOT)
    )


class TestKubernetesManifests:
    """Tests for Kubernetes manifest validation."""

    def test_kustomize_config_valid(self):
        """Test that kustomization.yaml is valid."""
        result = subprocess.run(
            ["kubectl", "kustomize", "k8s/"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0, f"Invalid kustomize config: {result.stderr}"

    def test_namespace_defined(self):
        """Test that namespace manifest exists."""
        result = subprocess.run(
            ["kubectl", "kustomize", "k8s/"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "kind: Namespace" in result.stdout
        assert "name: aax" in result.stdout


class TestKubernetesDeployments:
    """Tests for Kubernetes deployments."""

    def test_all_deployments_exist(self, k8s_deployed: Any) -> None:
        """Test that all expected deployments exist."""
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", "aax", "-o", "name"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        deployments = result.stdout.strip().split("\n")
        assert "deployment.apps/ee-base" in deployments
        assert "deployment.apps/ee-builder" in deployments
        assert "deployment.apps/dev-tools" in deployments

    def test_ee_base_deployment_ready(self, k8s_deployed: Any) -> None:
        """Test that ee-base deployment is ready."""
        for _ in range(30):
            result = subprocess.run(
                ["kubectl", "get", "deployment", "ee-base", "-n", "aax",
                 "-o", "jsonpath={.status.readyReplicas}"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() == "1":
                break
            time.sleep(2)
        else:
            pytest.fail("ee-base deployment did not become ready")

    def test_ee_builder_deployment_ready(self, k8s_deployed: Any) -> None:
        """Test that ee-builder deployment is ready."""
        for _ in range(30):
            result = subprocess.run(
                ["kubectl", "get", "deployment", "ee-builder", "-n", "aax",
                 "-o", "jsonpath={.status.readyReplicas}"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() == "1":
                break
            time.sleep(2)
        else:
            pytest.fail("ee-builder deployment did not become ready")

    def test_dev_tools_deployment_ready(self, k8s_deployed: Any) -> None:
        """Test that dev-tools deployment is ready."""
        for _ in range(30):
            result = subprocess.run(
                ["kubectl", "get", "deployment", "dev-tools", "-n", "aax",
                 "-o", "jsonpath={.status.readyReplicas}"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() == "1":
                break
            time.sleep(2)
        else:
            pytest.fail("dev-tools deployment did not become ready")


class TestKubernetesServices:
    """Tests for Kubernetes services."""

    def test_all_services_exist(self, k8s_deployed: Any) -> None:
        """Test that all expected services exist."""
        result = subprocess.run(
            ["kubectl", "get", "services", "-n", "aax", "-o", "name"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        services = result.stdout.strip().split("\n")
        assert "service/ee-base" in services
        assert "service/ee-builder" in services
        assert "service/dev-tools" in services

    def test_services_have_cluster_ip(self, k8s_deployed: Any) -> None:
        """Test that services have ClusterIP assigned."""
        for service in ["ee-base", "ee-builder", "dev-tools"]:
            result = subprocess.run(
                ["kubectl", "get", "service", service, "-n", "aax",
                 "-o", "jsonpath={.spec.clusterIP}"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip() != ""
            assert result.stdout.strip() != "None"


class TestKubernetesPods:
    """Tests for Kubernetes pods."""

    def test_all_pods_running(self, k8s_deployed: Any) -> None:
        """Test that all pods are running."""
        for _ in range(30):
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "aax",
                 "-o", "jsonpath={.items[*].status.phase}"],
                capture_output=True,
                text=True
            )
            phases = result.stdout.strip().split()
            if all(phase == "Running" for phase in phases) and len(phases) == 3:
                break
            time.sleep(2)
        else:
            pytest.fail("Not all pods are running")

    def test_pods_have_correct_labels(self, k8s_deployed: Any) -> None:
        """Test that pods have expected labels."""
        for app in ["ee-base", "ee-builder", "dev-tools"]:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "aax", "-l", f"app={app}",
                 "-o", "name"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip().startswith("pod/")


class TestKubernetesStorage:
    """Tests for Kubernetes persistent storage."""

    def test_all_pvcs_exist(self, k8s_deployed: Any) -> None:
        """Test that all PVCs are created."""
        result = subprocess.run(
            ["kubectl", "get", "pvc", "-n", "aax", "-o", "name"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        pvcs = result.stdout.strip().split("\n")
        assert "persistentvolumeclaim/workspace" in pvcs
        assert "persistentvolumeclaim/ee-builds" in pvcs
        assert "persistentvolumeclaim/ee-definitions" in pvcs
        assert "persistentvolumeclaim/dev-workspace" in pvcs

    def test_pvcs_are_bound(self, k8s_deployed: Any) -> None:
        """Test that all PVCs are bound."""
        for pvc in ["workspace", "ee-builds", "ee-definitions", "dev-workspace"]:
            result = subprocess.run(
                ["kubectl", "get", "pvc", pvc, "-n", "aax",
                 "-o", "jsonpath={.status.phase}"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "Bound"


class TestKubernetesFunctionality:
    """Tests for application functionality in Kubernetes."""

    def test_ee_base_ansible_works(self, k8s_deployed: Any) -> None:
        """Test that ansible command works in ee-base pod."""
        result = subprocess.run(
            ["kubectl", "exec", "-n", "aax", "deployment/ee-base", "--",
             "ansible", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "ansible [core 2.20.0]" in result.stdout

    def test_ee_builder_ansible_builder_works(self, k8s_deployed: Any) -> None:
        """Test that ansible-builder command works in ee-builder pod."""
        result = subprocess.run(
            ["kubectl", "exec", "-n", "aax", "deployment/ee-builder", "--",
             "ansible-builder", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "3.1" in result.stdout

    def test_dev_tools_ansible_navigator_works(self, k8s_deployed: Any) -> None:
        """Test that ansible-navigator command works in dev-tools pod."""
        result = subprocess.run(
            ["kubectl", "exec", "-n", "aax", "deployment/dev-tools", "--",
             "ansible-navigator", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "24.2.0" in result.stdout

    def test_dev_tools_ansible_lint_works(self, k8s_deployed: Any) -> None:
        """Test that ansible-lint command works in dev-tools pod."""
        result = subprocess.run(
            ["kubectl", "exec", "-n", "aax", "deployment/dev-tools", "--",
             "ansible-lint", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "25.12.1" in result.stdout


class TestKubernetesResources:
    """Tests for resource limits and requests."""

    def test_deployments_have_resource_limits(self, k8s_deployed: Any) -> None:
        """Test that deployments have resource limits configured."""
        for deployment in ["ee-base", "ee-builder", "dev-tools"]:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment, "-n", "aax",
                 "-o", "jsonpath={.spec.template.spec.containers[0].resources}"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            resources = result.stdout
            assert "limits" in resources
            assert "requests" in resources
            assert "cpu" in resources
            assert "memory" in resources


class TestKubernetesHealthChecks:
    """Tests for health checks and probes."""

    def test_deployments_have_health_checks(self, k8s_deployed: Any) -> None:
        """Test that deployments have liveness and readiness probes."""
        for deployment in ["ee-base", "ee-builder", "dev-tools"]:
            result = subprocess.run(
                ["kubectl", "get", "deployment", deployment, "-n", "aax",
                 "-o", "yaml"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            yaml_output = result.stdout
            assert "livenessProbe" in yaml_output
            assert "readinessProbe" in yaml_output


class TestKubernetesEnvironment:
    """Tests for environment variables."""

    def test_ansible_nocows_set(self, k8s_deployed: Any) -> None:
        """Test that ANSIBLE_NOCOWS is set in all pods."""
        for deployment in ["ee-base", "ee-builder", "dev-tools"]:
            result = subprocess.run(
                ["kubectl", "exec", "-n", "aax", f"deployment/{deployment}", "--",
                 "printenv", "ANSIBLE_NOCOWS"],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "1"

    def test_pager_disabled_in_dev_tools(self, k8s_deployed: Any) -> None:
        """Test that PAGER is disabled in dev-tools pod."""
        result = subprocess.run(
            ["kubectl", "exec", "-n", "aax", "deployment/dev-tools", "--",
             "printenv", "PAGER"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""
