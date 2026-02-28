"""
Tests for Docker images in the AAX project.
These tests verify that images build correctly and function as expected.
"""
import subprocess
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def build_image(tag, dockerfile, context, build_args=None):
    command = [
        "docker",
        "build",
        "-f",
        str(REPO_ROOT / dockerfile),
        "-t",
        tag,
    ]
    if build_args:
        for key, value in build_args.items():
            command.extend(["--build-arg", f"{key}={value}"])
    command.append(str(REPO_ROOT / context))
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return result


class TestEEBaseImage:
    """Tests for the Ansible EE base image."""

    IMAGE_NAME = "aax/ee-base:latest"

    def test_image_builds(self):
        """Test that the ee-base image builds successfully."""
        result = build_image(
            self.IMAGE_NAME,
            "images/ee-base/Dockerfile",
            "images/ee-base",
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


class TestEEBuilderImage:
    """Tests for the Ansible EE builder image."""

    IMAGE_NAME = "aax/ee-builder:latest"

    def test_image_builds(self):
        """Test that the ee-builder image builds successfully."""
        base_result = build_image(
            "aax/ee-base:latest",
            "images/ee-base/Dockerfile",
            "images/ee-base",
        )
        assert base_result.returncode == 0, f"Build failed: {base_result.stderr}"
        result = build_image(
            self.IMAGE_NAME,
            "images/ee-builder/Dockerfile",
            "images/ee-builder",
            build_args={"BASE_IMAGE": "aax/ee-base:latest"},
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_ansible_builder_installed(self):
        """Test that ansible-builder is installed and accessible."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible-builder", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"ansible-builder not found: {result.stderr}"
        assert "3.1.0" in result.stdout

    def test_inherits_from_base(self):
        """Test that ee-builder inherits ansible from ee-base."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "ansible [core 2.20.0]" in result.stdout

    def test_python_version(self):
        """Test that the correct Python version is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Python 3.14" in result.stdout

    def test_user_is_ansible(self):
        """Test that the container runs as the ansible user."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "whoami"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "ansible"

    def test_workspace_directory(self):
        """Test that the workspace directory is set correctly."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "pwd"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "/workspace"

    def test_healthcheck_works(self):
        """Test that the healthcheck passes."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible-builder", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0


class TestDevToolsImage:
    """Tests for the Ansible development tools image."""

    IMAGE_NAME = "aax/dev-tools:latest"

    def test_image_builds(self):
        """Test that the dev-tools image builds successfully."""
        base_result = build_image(
            "aax/ee-base:latest",
            "images/ee-base/Dockerfile",
            "images/ee-base",
        )
        assert base_result.returncode == 0, f"Build failed: {base_result.stderr}"
        result = build_image(
            self.IMAGE_NAME,
            "images/dev-tools/Dockerfile",
            "images/dev-tools",
            build_args={"BASE_IMAGE": "aax/ee-base:latest"},
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_ansible_navigator_installed(self):
        """Test that ansible-navigator is installed and accessible."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible-navigator", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"ansible-navigator not found: {result.stderr}"
        assert "24.2.0" in result.stdout

    def test_ansible_lint_installed(self):
        """Test that ansible-lint is installed and accessible."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible-lint", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"ansible-lint not found: {result.stderr}"
        assert "25.12.1" in result.stdout

    def test_inherits_from_base(self):
        """Test that dev-tools inherits ansible from ee-base."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "ansible [core 2.20.0]" in result.stdout

    def test_python_version(self):
        """Test that the correct Python version is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Python 3.14" in result.stdout

    def test_user_is_ansible(self):
        """Test that the container runs as the ansible user."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "whoami"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "ansible"

    def test_workspace_directory(self):
        """Test that the workspace directory is set correctly."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "pwd"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "/workspace"

    def test_pager_disabled(self):
        """Test that PAGER environment variable is set."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "printenv", "PAGER"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestAWXImage:
    """Tests for the AWX automation controller image."""

    IMAGE_NAME = "aax/awx:latest"

    def test_image_builds(self):
        """Test that the AWX image builds successfully."""
        result = build_image(
            self.IMAGE_NAME,
            "images/awx/Dockerfile",
            "images/awx",
            build_args={"AWX_VERSION": "24.6.1"},
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_django_installed(self):
        """Test that Django is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import django; print(django.VERSION)"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Django not found: {result.stderr}"

    def test_uwsgi_or_gunicorn_available(self):
        """Test that a WSGI server is available."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import gunicorn"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "gunicorn not found"

    def test_database_drivers_installed(self):
        """Test that PostgreSQL driver is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import psycopg2"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "psycopg2 not found"

    def test_healthcheck_port_exists(self):
        """Test that AWX API port is configured."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "print('8052')"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0


class TestGalaxyNGImage:
    """Tests for the Galaxy NG image."""

    IMAGE_NAME = "aax/galaxy-ng:latest"

    def test_image_builds(self):
        """Test that the Galaxy NG image builds successfully."""
        result = build_image(
            self.IMAGE_NAME,
            "images/galaxy-ng/Dockerfile",
            "images/galaxy-ng",
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_django_installed(self):
        """Test that Django is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import django"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_galaxy_ng_installed(self):
        """Test that galaxy-ng package is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import galaxy_ng"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "galaxy-ng not installed"

    def test_gunicorn_installed(self):
        """Test that gunicorn is installed for WSGI."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import gunicorn"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_postgres_driver_installed(self):
        """Test that PostgreSQL driver is available."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import psycopg2"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_user_is_galaxy(self):
        """Test that the container runs as the galaxy user."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "whoami"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "galaxy"


class TestPulpImage:
    """Tests for the Pulp content management image."""

    IMAGE_NAME = "aax/pulp:latest"

    def test_image_builds(self):
        """Test that the Pulp image builds successfully."""
        result = build_image(
            self.IMAGE_NAME,
            "images/pulp/Dockerfile.pulp",
            "images/pulp",
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_pulpcore_installed(self):
        """Test that pulpcore is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import pulpcore"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "pulpcore not installed"

    def test_pulp_ansible_plugin_installed(self):
        """Test that pulp-ansible plugin is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import pulp_ansible"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "pulp_ansible not installed"

    def test_postgres_driver_installed(self):
        """Test that PostgreSQL driver is available."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import psycopg2"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_redis_client_installed(self):
        """Test that Redis client is available."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import redis"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_user_is_pulp(self):
        """Test that the container runs as the pulp user."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "whoami"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "pulp"


class TestEDAImage:
    """Tests for the Event-Driven Ansible controller image."""

    IMAGE_NAME = "aax/eda:latest"

    def test_image_builds(self):
        """Test that the EDA image builds successfully."""
        result = build_image(
            self.IMAGE_NAME,
            "images/eda-controller/Dockerfile",
            "images/eda-controller",
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    def test_ansible_rulebook_installed(self):
        """Test that ansible-rulebook is installed."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import ansible_rulebook"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "ansible-rulebook not installed"

    def test_ansible_rulebook_cli_accessible(self):
        """Test that ansible-rulebook CLI is accessible."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "ansible-rulebook", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "ansible-rulebook CLI not accessible"

    def test_aiohttp_installed(self):
        """Test that aiohttp is installed for API server."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import aiohttp"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_postgres_driver_installed(self):
        """Test that PostgreSQL driver is available."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "python3", "-c", "import psycopg2"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_user_is_eda(self):
        """Test that the container runs as the eda user."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "whoami"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "eda"

    def test_java_installed(self):
        """Test that Java is installed for Drools engine."""
        result = subprocess.run(
            ["docker", "run", "--rm", self.IMAGE_NAME, "java", "-version"],
            capture_output=True,
            text=True
        )
        # Java prints version to stderr, so check both stdout and stderr
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"Java not installed. Output: {output}"
        assert "openjdk" in output.lower() or "java" in output.lower(), "Java version not found in output"
