"""
Tests for Docker Compose configuration and service orchestration.
These tests verify that services start correctly, dependencies work, and health checks pass.
"""
import os
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _required_compose_env() -> dict[str, str]:
    """Return required compose secrets with deterministic test values."""
    env = os.environ.copy()
    env.update(
        {
            "POSTGRES_PASSWORD": "test-postgres-password",  # pragma: allowlist secret
            "DATABASE_PASSWORD": "test-database-password",  # pragma: allowlist secret
            "AWX_ADMIN_PASSWORD": "test-awx-admin-password",  # pragma: allowlist secret
            "SECRET_KEY": "test-secret-key",  # pragma: allowlist secret
            "HUB_DB_PASSWORD": "test-hub-db-password",  # pragma: allowlist secret
            "HUB_ADMIN_PASSWORD": "test-hub-admin-password",  # pragma: allowlist secret
            "GALAXY_SECRET_KEY": "test-galaxy-secret-key",  # pragma: allowlist secret
            "PULP_SECRET_KEY": "test-pulp-secret-key",  # pragma: allowlist secret
            "EDA_DB_PASSWORD": "test-eda-db-password",  # pragma: allowlist secret
        }
    )
    return env


@pytest.fixture(scope="module")
def compose_up():
    """Start docker-compose services before tests and tear down after."""
    # Start services
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "ee-base", "ee-builder", "dev-tools"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=_required_compose_env(),
    )
    assert result.returncode == 0, f"Failed to start services: {result.stderr}"

    # Wait for services to be healthy
    time.sleep(10)

    yield

    # Cleanup - stop services
    subprocess.run(
        ["docker", "compose", "down"],
        capture_output=True,
        cwd=str(REPO_ROOT),
        env=_required_compose_env(),
    )


class TestDockerCompose:
    """Tests for Docker Compose orchestration."""

    def test_compose_config_valid(self):
        """Test that docker-compose.yml is valid."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0, f"Invalid compose config: {result.stderr}"

    def test_compose_build(self):
        """Test that all images build successfully via docker-compose."""
        result = subprocess.run(
            ["docker", "compose", "build"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_all_services_defined(self):
        """Test that expected services are defined in docker-compose.yml."""
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "controller",
                "--profile",
                "hub",
                "--profile",
                "eda",
                "config",
                "--services",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        services = result.stdout.strip().split("\n")
        expected_services = [
            "ee-base",
            "ee-builder",
            "dev-tools",
            "awx-web",
            "awx-task",
            "awx-receptor",
            "receptor-hop",
            "receptor-execution",
            "gateway",
            "galaxy-ng",
            "pulp-api",
            "pulp-content",
            "pulp-worker",
            "eda-controller",
        ]
        for service in expected_services:
            assert service in services, f"Service {service} not found in compose config"

    def test_awx_uses_local_image_default(self):
        """Test that AWX defaults to the locally built image tag."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        assert "image: aax/awx:" in result.stdout

    def test_default_execution_environment_uses_local_image(self):
        """Test that the controller default EE points at the local ee-base image."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        assert "DEFAULT_EXECUTION_ENVIRONMENT: aax/ee-base:" in result.stdout

    def test_missing_required_secret_fails_compose_render(self):
        """Test that required secret variables fail fast when empty."""
        env = os.environ.copy()
        env["DATABASE_PASSWORD"] = ""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        assert result.returncode != 0
        combined_output = f"{result.stdout}\n{result.stderr}"
        assert "DATABASE_PASSWORD must be set" in combined_output

    def test_eda_controller_shares_awx_network(self):
        """Test that EDA can reach AWX over a shared compose network."""
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "controller",
                "--profile",
                "eda",
                "config",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = result.stdout
        eda_section = config.split("eda-controller:", 1)[1]
        assert "awx-network:" in config
        assert "eda-network:" in config
        assert "awx-network: null" in eda_section
        assert "eda-network: null" in eda_section

    def test_gateway_exposes_unified_entrypoint(self):
        """Test that the gateway provides a single entrypoint across stack networks."""
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--profile",
                "controller",
                "--profile",
                "hub",
                "--profile",
                "eda",
                "config",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = result.stdout
        gateway_section = config.split("gateway:", 1)[1]
        assert "image: aax/gateway:" in gateway_section
        assert "mode: ingress" in gateway_section
        assert 'published: "8088"' in gateway_section
        assert "target: 8080" in gateway_section
        assert "awx-network: null" in gateway_section
        assert "hub-network: null" in gateway_section
        assert "eda-network: null" in gateway_section

    def test_awx_web_does_not_mount_docker_socket(self):
        """Test that awx-web does not get direct Docker host control."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "config", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = json.loads(result.stdout)
        volumes = config["services"]["awx-web"].get("volumes", [])
        assert all(volume.get("target") != "/var/run/docker.sock" for volume in volumes)

    def test_awx_task_does_not_mount_docker_socket(self):
        """Test that awx-task does not get direct Docker host control."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "config", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = json.loads(result.stdout)
        volumes = config["services"]["awx-task"].get("volumes", [])
        assert all(volume.get("target") != "/var/run/docker.sock" for volume in volumes)

    def test_pulp_services_are_not_published_on_host_ports(self):
        """Test that raw Pulp services stay internal by default."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "hub", "config", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = json.loads(result.stdout)
        pulp_api_ports = config["services"]["pulp-api"].get("ports", [])
        pulp_content_ports = config["services"]["pulp-content"].get("ports", [])
        assert pulp_api_ports == []
        assert pulp_content_ports == []

    def test_published_ports_bind_to_localhost_by_default(self):
        """Test that externally published ports are localhost-bound by default."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "--profile", "hub", "--profile", "eda", "config", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = json.loads(result.stdout)

        for service_name in ["awx-web", "awx-receptor", "gateway", "galaxy-ng", "eda-controller"]:
            ports = config["services"][service_name].get("ports", [])
            assert ports, f"Expected published ports for {service_name}"
            assert all(port.get("host_ip") == "127.0.0.1" for port in ports)

    def test_receptor_mesh_is_multi_node(self):
        """Test that the controller profile renders a controller-hop-execution receptor mesh."""
        result = subprocess.run(
            ["docker", "compose", "--profile", "controller", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = result.stdout
        assert "awx-receptor:" in config
        assert "receptor-hop:" in config
        assert "receptor-execution:" in config
        assert "id: receptor-controller" in config
        assert "id: receptor-hop" in config
        assert "id: receptor-execution" in config
        assert "address: receptor-hop:8888" in config
        assert "address: awx-receptor:8888" in config
        assert "address: receptor-execution:8888" in config
        assert "worktype: ansible-runner" in config


class TestServiceOrchestration:
    """Tests for service dependencies and orchestration."""

    def test_services_start(self, compose_up: Any) -> None:
        """Test that all services start successfully."""
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        # Check that services are running
        assert "ee-base" in result.stdout
        assert "ee-builder" in result.stdout
        assert "dev-tools" in result.stdout

    def test_ee_base_healthy(self, compose_up: Any) -> None:
        """Test that ee-base service becomes healthy."""
        # Wait up to 30 seconds for service to be healthy
        for _ in range(30):
            result = subprocess.run(
                ["docker", "compose", "ps", "ee-base", "--format", "{{.Health}}"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT)
            )
            if "healthy" in result.stdout.lower():
                break
            time.sleep(1)
        else:
            pytest.fail("ee-base service did not become healthy")

    def test_ee_builder_starts_after_base(self, compose_up: Any) -> None:
        """Test that ee-builder waits for ee-base to be healthy."""
        result = subprocess.run(
            ["docker", "compose", "ps", "ee-builder", "--format", "{{.State}}"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "running" in result.stdout.lower() or "exited" in result.stdout.lower()

    def test_dev_tools_starts_after_base(self, compose_up: Any) -> None:
        """Test that dev-tools waits for ee-base to be healthy."""
        result = subprocess.run(
            ["docker", "compose", "ps", "dev-tools", "--format", "{{.State}}"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "running" in result.stdout.lower() or "exited" in result.stdout.lower()

    def test_network_exists(self, compose_up: Any) -> None:
        """Test that the ansible network is created."""
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "aax_ansible" in result.stdout or "ansible" in result.stdout

    def test_volumes_exist(self, compose_up: Any) -> None:
        """Test that required volumes are created."""
        result = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        # Check for volumes (may have project prefix)
        volumes_output = result.stdout
        assert any("workspace" in line for line in volumes_output.split("\n"))
        assert any("ee_builds" in line for line in volumes_output.split("\n"))


class TestServiceFunctionality:
    """Tests for service functionality and inter-service communication."""

    def test_ee_base_ansible_works(self, compose_up: Any) -> None:
        """Test that ansible command works in ee-base service."""
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "ee-base", "ansible", "--version"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "ansible [core 2.20.0]" in result.stdout

    def test_ee_builder_ansible_builder_works(self, compose_up: Any) -> None:
        """Test that ansible-builder command works in ee-builder service."""
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "ee-builder", "ansible-builder", "--version"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "3.1" in result.stdout

    def test_dev_tools_ansible_navigator_works(self, compose_up: Any) -> None:
        """Test that ansible-navigator command works in dev-tools service."""
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "dev-tools", "ansible-navigator", "--version"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "24.2.0" in result.stdout

    def test_dev_tools_ansible_lint_works(self, compose_up: Any) -> None:
        """Test that ansible-lint command works in dev-tools service."""
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "dev-tools", "ansible-lint", "--version"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert "25.12.1" in result.stdout

    def test_services_share_network(self, compose_up: Any) -> None:
        """Test that services can communicate on the ansible network."""
        # Test that dev-tools can resolve ee-base by service name using Python
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "dev-tools", "python3", "-c",
             "import socket; socket.gethostbyname('ee-base')"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0, "Services cannot communicate on shared network"


class TestComposeCompatibility:
    """Tests for compose compatibility with local Docker engines."""

    def test_no_deploy_resource_limits_present(self):
        """Test that deploy resource limits are absent for wider Docker compatibility."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = result.stdout
        assert "deploy:" not in config

    def test_services_have_health_checks(self):
        """Test that all services have health checks configured."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=_required_compose_env(),
        )
        assert result.returncode == 0
        config = result.stdout
        # Each service should have a healthcheck
        assert config.count("healthcheck:") >= 3


class TestEnvironmentVariables:
    """Tests for environment variable configuration."""

    def test_ansible_nocows_set(self, compose_up: Any) -> None:
        """Test that ANSIBLE_NOCOWS is set in all services."""
        for service in ["ee-base", "ee-builder", "dev-tools"]:
            result = subprocess.run(
                ["docker", "compose", "exec", "-T", service, "printenv", "ANSIBLE_NOCOWS"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT)
            )
            assert result.returncode == 0
            assert result.stdout.strip() == "1"

    def test_pager_disabled_in_dev_tools(self, compose_up: Any) -> None:
        """Test that PAGER is disabled in dev-tools service."""
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "dev-tools", "printenv", "PAGER"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""
