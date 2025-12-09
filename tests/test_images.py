"""
Tests for Docker images in the AAX project.
These tests verify that images build correctly and function as expected.
"""
import subprocess
import pytest


class TestEEBaseImage:
    """Tests for the Ansible EE base image."""

    IMAGE_NAME = "aax/ee-base:latest"

    def test_image_builds(self):
        """Test that the ee-base image builds successfully."""
        result = subprocess.run(
            ["make", "build-ee-base"],
            capture_output=True,
            text=True,
            cwd="/workspaces/AAX"
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_ansible_installed(self):
        """Test that Ansible is installed and accessible."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Ansible not found: {result.stderr}"
        assert "ansible [core 2.20.0]" in result.stdout

    def test_ansible_runner_installed(self):
        """Test that ansible-runner is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible-runner", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"ansible-runner not found: {result.stderr}"
        assert "2.4.2" in result.stdout

    def test_python_version(self):
        """Test that the correct Python version is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Python 3.14" in result.stdout

    def test_required_packages(self):
        """Test that required system packages are installed."""
        packages = ["git", "ssh", "rsync", "jq", "curl"]
        for package in packages:
            result = subprocess.run(
                ["docker", "run", "--rm", self.IMAGE_NAME, "which", package],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0, f"Package {package} not found"

    def test_ansible_config_exists(self):
        """Test that ansible.cfg is in the correct location."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "cat", "/etc/ansible/ansible.cfg"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "host_key_checking = False" in result.stdout

    def test_user_is_ansible(self):
        """Test that the container runs as the ansible user."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "whoami"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "ansible"

    def test_entrypoint_works(self):
        """Test that the entrypoint script works correctly."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "echo", "test"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "test" in result.stdout

    def test_ansible_imports(self):
        """Test that Python can import Ansible modules."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c",
             "import ansible; import ansible_runner; print('success')"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "success" in result.stdout
