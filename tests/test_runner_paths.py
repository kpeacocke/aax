"""Exercise the worker mappings used by AWX inventory imports."""

import os
import subprocess
import shutil
import signal
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("service", ["awx-receptor", "receptor-execution"])
def test_inventory_input_and_output_follow_current_job(tmp_path, service):
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    command = compose["services"][service]["command"][-1]
    wrapper = command.split("cat > /usr/local/bin/ansible-runner-locked << 'WEOF'\n")[1]
    wrapper = wrapper.split("\nWEOF", 1)[0].replace("$$", "$")
    runner_root = tmp_path / "runner"
    wrapper = wrapper.replace("/runner", str(runner_root))
    script = tmp_path / "worker.sh"
    script.write_text(wrapper)
    executable = tmp_path / "ansible-runner"
    executable.write_text(
        '#!/bin/sh\nset -eu\n'
        f'cat "{runner_root}/project/hosts.yml"\n'
        f'cat "{runner_root}/env/settings"\n'
        f'printf imported > "{runner_root}/artifacts/output.json"\n'
    )
    executable.chmod(0o700)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}")
    # Reuse the worker for two jobs: none of the compatibility links may retain
    # the previous job's input, credential directory or output destination.
    for number in (1, 2):
        private = tmp_path / f"job-{number}"
        for directory in ("project", "env", "artifacts"):
            (private / directory).mkdir(parents=True)
        (private / "project/hosts.yml").write_text(f"host-{number}\n")
        (private / "env/settings").write_text(f"settings-{number}\n")
        result = subprocess.run(
            ["sh", str(script), f"--private-data-dir={private}"],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        assert result.stdout == f"host-{number}\nsettings-{number}\n"
        assert (private / "artifacts/output.json").read_text() == "imported"


@pytest.mark.skipif(shutil.which("flock") is None, reason="Linux util-linux flock required")
@pytest.mark.parametrize("service", ["awx-receptor", "receptor-execution"])
def test_runner_orphan_cannot_retain_supervisor_lock(tmp_path, service):
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    command = compose["services"][service]["command"][-1]
    wrapper = command.split("cat > /usr/local/bin/ansible-runner-worker << 'WEOF'\n")[1]
    wrapper = wrapper.split("\nWEOF", 1)[0].replace("$$", "$")
    lock = tmp_path / "lock"
    child = tmp_path / "child.sh"
    ready = tmp_path / "ready"
    child.write_text(f'#!/bin/sh\necho $$ > "{ready}"\nexec sleep 30\n')
    child.chmod(0o700)
    wrapper = wrapper.replace("/tmp/aax-ansible-runner.lock", str(lock))
    wrapper = wrapper.replace("/usr/local/bin/ansible-runner-locked", str(child))
    script = tmp_path / "worker.sh"
    script.write_text(wrapper)
    supervisor = subprocess.Popen(["sh", str(script)])
    orphan_pid = None
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists(), "worker never started"
        orphan_pid = int(ready.read_text())
        assert subprocess.run(["flock", "-n", str(lock), "true"]).returncode == 1
        supervisor.terminate()
        supervisor.wait(timeout=5)
        # The live failure left a worker orphaned after its supervisor exited.
        # It must not retain the lock and block every subsequent job.
        os.kill(orphan_pid, 0)
        assert subprocess.run(["flock", "-n", str(lock), "true"]).returncode == 0
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait(timeout=5)
        if orphan_pid is not None:
            try:
                os.kill(orphan_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
