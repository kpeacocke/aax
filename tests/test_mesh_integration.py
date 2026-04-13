"""Integration tests that spin up the real AWX controller stack and run jobs.

These tests require Docker and are marked with ``@pytest.mark.integration``.
They are excluded from the default ``pytest`` run.  Execute them with::

    pytest -m integration tests/test_mesh_integration.py -v --no-cov

Set ``AWX_WEB_PORT`` to match the port AWX is exposed on (default 18080).

If the stack is already running the tests reuse it and skip teardown.
To force a fresh stack, set ``AAX_FRESH_STACK=1``.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any, Generator

import pytest
import requests
from requests.auth import HTTPBasicAuth

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

# AWX connection defaults
AWX_USER = os.getenv("AWX_ADMIN_USER", "admin")
AWX_PASS = os.getenv("AWX_ADMIN_PASSWORD", "password")
AWX_PORT = os.getenv("AWX_WEB_PORT", "18080")
AWX_URL = f"http://localhost:{AWX_PORT}"
AUTH = HTTPBasicAuth(AWX_USER, AWX_PASS)

# Timeout configuration
STACK_READY_TIMEOUT = 600  # 10 min for images to pull + migrations
JOB_TIMEOUT = 120  # 2 min per job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compose_env() -> dict[str, str]:
    """Return a minimal env dict for docker compose with test-safe secrets."""
    env = os.environ.copy()
    env.setdefault("DATABASE_PASSWORD", "integration-test-pw")
    env.setdefault("SECRET_KEY", "integration-test-secret-key-not-for-production")
    env.setdefault("AAX_ALLOW_PLACEHOLDER_SECRETS", "true")
    env.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")
    env.setdefault("AWX_ADMIN_USER", AWX_USER)
    env.setdefault("AWX_ADMIN_PASSWORD", AWX_PASS)
    return env


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [
        "docker", "compose",
        "-f", str(COMPOSE_FILE),
        "--profile", "controller",
        *args,
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=str(REPO_ROOT), env=_compose_env(), check=check,
    )


def _awx_api(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{AWX_URL}{path}"
    resp = requests.request(method, url, auth=AUTH, timeout=30, **kwargs)
    return resp


def _wait_for_awx(timeout: int = STACK_READY_TIMEOUT) -> None:
    """Block until AWX responds to /api/v2/ping/."""
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            r = requests.get(f"{AWX_URL}/api/v2/ping/", timeout=5)
            if r.status_code == 200:
                return
        except Exception as exc:
            last_exc = exc
        time.sleep(5)
    raise TimeoutError(
        f"AWX did not become ready within {timeout}s.  Last error: {last_exc}"
    )


def _wait_for_job(job_id: int, timeout: int = JOB_TIMEOUT) -> dict[str, Any]:
    """Poll a job until it reaches a terminal state."""
    deadline = time.monotonic() + timeout
    terminal = {"successful", "failed", "error", "canceled"}
    while time.monotonic() < deadline:
        r = _awx_api("GET", f"/api/v2/jobs/{job_id}/")
        r.raise_for_status()
        data = r.json()
        if data["status"] in terminal:
            return data
        time.sleep(3)
    raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")


def _wait_for_project_sync(project_id: int, timeout: int = JOB_TIMEOUT) -> dict[str, Any]:
    """Poll project updates until the latest one finishes."""
    deadline = time.monotonic() + timeout
    terminal = {"successful", "failed", "error", "canceled", "never updated"}
    while time.monotonic() < deadline:
        r = _awx_api("GET", f"/api/v2/projects/{project_id}/")
        r.raise_for_status()
        data = r.json()
        if data["status"] in terminal:
            return data
        time.sleep(3)
    raise TimeoutError(f"Project {project_id} sync did not finish within {timeout}s")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _stack_is_running() -> bool:
    """Return True if the AWX API is already responding."""
    try:
        r = requests.get(f"{AWX_URL}/api/v2/ping/", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def awx_stack() -> Generator[None, None, None]:
    """Bring up the controller stack for the entire test session.

    If the stack is already running (API responds), reuse it and skip teardown.
    Set ``AAX_FRESH_STACK=1`` to force a fresh stack.
    """
    reuse = _stack_is_running() and not os.getenv("AAX_FRESH_STACK")
    if reuse:
        print("\n[integration] Stack already running, reusing it")
        # Ensure admin credentials work
        _ensure_admin()
        yield
        return

    _compose("down", "-v", "--remove-orphans", check=False)

    print("\n[integration] Starting AWX controller stack...")
    result = _compose("up", "-d", "--wait", check=False)
    if result.returncode != 0:
        print(f"[integration] compose up returned {result.returncode}")
        print(result.stderr[-2000:] if result.stderr else "")

    try:
        _wait_for_awx()
        print("[integration] AWX is ready")
        _ensure_admin()
        yield
    finally:
        print("\n[integration] Tearing down AWX controller stack...")
        logs = _compose("logs", "--tail", "200", check=False)
        if logs.stdout:
            log_file = REPO_ROOT / "integration-test-logs.txt"
            log_file.write_text(logs.stdout[-50000:])
            print(f"[integration] Logs saved to {log_file}")
        _compose("down", "-v", "--remove-orphans", check=False)


def _ensure_admin() -> None:
    """Create/reset the admin user via docker exec."""
    _compose(
        "exec", "-T", "awx-web",
        "awx-manage", "createsuperuser",
        "--username", AWX_USER,
        "--email", "admin@localhost",
        "--noinput",
        check=False,
    )
    # set_password via Django shell (update_password is unreliable)
    _compose(
        "exec", "-T", "awx-web",
        "awx-manage", "shell", "-c",
        f"from django.contrib.auth.models import User; "
        f"u = User.objects.get(username='{AWX_USER}'); "
        f"u.set_password('{AWX_PASS}'); u.save()",
        check=False,
    )


@pytest.fixture(scope="session")
def hello_world_project(awx_stack: None, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a local hello-world playbook directory and copy it into AWX."""
    project_dir = tmp_path_factory.mktemp("hello_world")
    playbook = project_dir / "hello.yml"
    playbook.write_text(textwrap.dedent("""\
        ---
        - name: Hello World
          hosts: all
          gather_facts: false
          tasks:
            - name: Say hello
              ansible.builtin.debug:
                msg: "Hello from AAX integration test!"
    """))
    # Use docker cp to copy into the awx_projects volume via the awx-task container
    # (awx-task, awx-web, and awx-receptor all share that volume)
    subprocess.run(
        ["docker", "cp", str(project_dir) + "/.", "awx-task:/var/lib/awx/projects/hello_world/"],
        check=True, capture_output=True,
    )
    return project_dir


@pytest.fixture(scope="session")
def awx_organization(awx_stack: None) -> int:
    """Return the ID of the Default organization (created by AWX on first boot)."""
    r = _awx_api("GET", "/api/v2/organizations/", params={"name": "Default"})
    r.raise_for_status()
    results = r.json()["results"]
    assert results, "Default organization not found"
    return results[0]["id"]


@pytest.fixture(scope="session")
def awx_inventory(awx_organization: int) -> Generator[int, None, None]:
    """Get or create a test inventory with localhost."""
    r = _awx_api("GET", "/api/v2/inventories/", params={
        "name": "integration-test-inventory",
        "organization": awx_organization,
    })
    r.raise_for_status()
    # Skip inventories that are pending deletion
    existing = [i for i in r.json()["results"] if not i.get("pending_deletion")]
    if existing:
        inv_id = existing[0]["id"]
        # Ensure localhost host exists
        hr = _awx_api("GET", f"/api/v2/inventories/{inv_id}/hosts/", params={"name": "localhost"})
        if hr.ok and hr.json()["count"] == 0:
            _awx_api("POST", f"/api/v2/inventories/{inv_id}/hosts/", json={
                "name": "localhost",
                "variables": "ansible_connection: local\nansible_python_interpreter: /usr/bin/python3",
            })
        yield inv_id
        return

    r = _awx_api("POST", "/api/v2/inventories/", json={
        "name": "integration-test-inventory",
        "organization": awx_organization,
    })
    r.raise_for_status()
    inv_id = r.json()["id"]

    _awx_api("POST", f"/api/v2/inventories/{inv_id}/hosts/", json={
        "name": "localhost",
        "variables": "ansible_connection: local\nansible_python_interpreter: /usr/bin/python3",
    }).raise_for_status()

    yield inv_id


@pytest.fixture(scope="session")
def awx_project(awx_organization: int, hello_world_project: Path) -> Generator[int, None, None]:
    """Get or create a manual SCM project pointing at the hello_world directory."""
    r = _awx_api("GET", "/api/v2/projects/", params={
        "name": "integration-test-project",
        "organization": awx_organization,
    })
    r.raise_for_status()
    existing = r.json()["results"]
    if existing:
        yield existing[0]["id"]
        return

    r = _awx_api("POST", "/api/v2/projects/", json={
        "name": "integration-test-project",
        "organization": awx_organization,
        "scm_type": "",  # manual
        "local_path": "hello_world",
    })
    r.raise_for_status()
    yield r.json()["id"]


@pytest.fixture(scope="session")
def awx_job_template(awx_project: int, awx_inventory: int) -> Generator[int, None, None]:
    """Get or create a job template using the hello-world project."""
    r = _awx_api("GET", "/api/v2/job_templates/", params={
        "name": "integration-test-hello-world",
    })
    r.raise_for_status()
    existing = r.json()["results"]
    if existing:
        jt = existing[0]
        # Patch project/inventory to current values (may have drifted)
        _awx_api("PATCH", f"/api/v2/job_templates/{jt['id']}/", json={
            "project": awx_project,
            "inventory": awx_inventory,
        })
        yield jt["id"]
        return

    # Need to get the default EE
    r = _awx_api("GET", "/api/v2/execution_environments/", params={"name": "Default Execution Environment"})
    r.raise_for_status()
    ee_results = r.json()["results"]

    jt_data: dict[str, Any] = {
        "name": "integration-test-hello-world",
        "project": awx_project,
        "inventory": awx_inventory,
        "playbook": "hello.yml",
        "verbosity": 2,
    }
    if ee_results:
        jt_data["execution_environment"] = ee_results[0]["id"]

    r = _awx_api("POST", "/api/v2/job_templates/", json=jt_data)
    r.raise_for_status()
    yield r.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestMeshIntegration:
    """Tests that validate the receptor mesh by running real AWX jobs."""

    def test_awx_api_healthy(self, awx_stack: None) -> None:
        """AWX /api/v2/ping/ returns 200."""
        r = _awx_api("GET", "/api/v2/ping/")
        assert r.status_code == 200

    def test_receptor_mesh_connected(self, awx_stack: None) -> None:
        """The receptor mesh has at least 2 nodes (awx + receptor-execution)."""
        r = _awx_api("GET", "/api/v2/instances/")
        r.raise_for_status()
        instances = r.json()["results"]
        hostnames = {i["hostname"] for i in instances}
        assert "awx" in hostnames, f"Expected 'awx' in instances, got {hostnames}"
        # receptor-execution should be provisioned
        assert "receptor-execution" in hostnames, (
            f"Expected 'receptor-execution' in instances, got {hostnames}"
        )

    def test_instances_healthy(self, awx_stack: None) -> None:
        """All instances report non-zero capacity."""
        r = _awx_api("GET", "/api/v2/instances/")
        r.raise_for_status()
        for inst in r.json()["results"]:
            if inst["enabled"]:
                assert inst["capacity"] > 0, (
                    f"Instance {inst['hostname']} has zero capacity "
                    f"(node_type={inst['node_type']}, errors={inst.get('errors','')})"
                )

    def test_project_sync_succeeds(self, awx_project: int) -> None:
        """A manual project is available (status 'ok' or 'successful')."""
        r = _awx_api("GET", f"/api/v2/projects/{awx_project}/")
        r.raise_for_status()
        data = r.json()
        # Manual projects don't need a sync — they should be 'ok' or never updated
        assert data["status"] in ("ok", "successful", "never updated"), (
            f"Project status is '{data['status']}', "
            f"last_job_failed: {data.get('last_job_failed')}"
        )

    def test_hello_world_job_succeeds(self, awx_job_template: int) -> None:
        """Launch the hello-world job template and verify it completes successfully."""
        # Launch
        r = _awx_api("POST", f"/api/v2/job_templates/{awx_job_template}/launch/")
        assert r.status_code in (200, 201), f"Launch failed: {r.status_code} {r.text}"
        job_id = r.json()["id"]

        # Wait for completion
        job_data = _wait_for_job(job_id)
        status = job_data["status"]

        # On failure, grab stdout for diagnostics
        if status != "successful":
            stdout_r = _awx_api("GET", f"/api/v2/jobs/{job_id}/stdout/",
                                params={"format": "txt"})
            stdout_text = stdout_r.text[:3000] if stdout_r.ok else "(could not fetch)"
            pytest.fail(
                f"Job {job_id} finished with status '{status}'.\n"
                f"Explanation: {job_data.get('job_explanation', 'N/A')}\n"
                f"Result traceback: {job_data.get('result_traceback', 'N/A')}\n"
                f"Stdout (first 3000 chars):\n{stdout_text}"
            )

        # Verify we got events (host_status_counts may lag behind status)
        for _ in range(10):
            fresh = _awx_api("GET", f"/api/v2/jobs/{job_id}/").json()
            host_counts = fresh.get("host_status_counts") or {}
            if host_counts.get("ok", 0) >= 1:
                break
            time.sleep(1)
        assert host_counts.get("ok", 0) >= 1, (
            f"Expected at least 1 OK host, got: {fresh.get('host_status_counts')}"
        )

    def test_job_stdout_contains_hello(self, awx_job_template: int) -> None:
        """Verify the job output contains our hello-world message."""
        # Find the latest successful job for this template
        r = _awx_api("GET", "/api/v2/jobs/", params={
            "job_template": awx_job_template,
            "status": "successful",
            "order_by": "-id",
            "page_size": 1,
        })
        r.raise_for_status()
        results = r.json()["results"]
        if not results:
            pytest.skip("No successful jobs found (run test_hello_world_job_succeeds first)")

        job_id = results[0]["id"]
        stdout_r = _awx_api("GET", f"/api/v2/jobs/{job_id}/stdout/",
                            params={"format": "txt"})
        stdout_r.raise_for_status()
        assert "Hello from AAX integration test!" in stdout_r.text
