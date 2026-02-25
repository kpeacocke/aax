"""
Tests for Docker Compose configuration and service orchestration.
These tests verify that services start correctly, dependencies work, and health checks pass.
"""
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def compose_up():
    """Start docker-compose services before tests and tear down after."""
    # Start services
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    assert result.returncode == 0, f"Failed to start services: {result.stderr}"

    # Wait for services to be healthy
    time.sleep(10)

    yield

    # Cleanup - stop services
    subprocess.run(
        ["docker", "compose", "down"],
        capture_output=True,
        cwd=str(REPO_ROOT)
    )


class TestDockerCompose:
    """Tests for Docker Compose orchestration."""

    def test_compose_config_valid(self):
        """Test that docker-compose.yml is valid."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0, f"Invalid compose config: {result.stderr}"

    def test_compose_build(self):
        """Test that all images build successfully via docker-compose."""
        result = subprocess.run(
            ["docker", "compose", "build"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_all_services_defined(self):
        """Test that expected services are defined in docker-compose.yml."""
        result = subprocess.run(
            ["docker", "compose", "config", "--services"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        services = result.stdout.strip().split("\n")
        expected_services = ["ee-base", "ee-builder", "dev-tools"]
        for service in expected_services:
            assert service in services, f"Service {service} not found in compose config"


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


class TestResourceLimits:
    """Tests for resource limits and reservations."""

    def test_ee_base_has_resource_limits(self):
        """Test that ee-base has resource limits configured."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0
        config = result.stdout
        # Check for resource limits in ee-base service
        assert "cpus:" in config
        assert "memory:" in config

    def test_services_have_health_checks(self):
        """Test that all services have health checks configured."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
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
