"""Patch AWX jobs.py for containerised execution.

In a Docker Compose deployment the execution node IS a container, so
process isolation (podman/bwrap) is unnecessary and unavailable.  This
script runs once at awx-task startup and:

  1. Disables process_isolation (True → False)
  2. Makes the isolation executable env-configurable as a safety net
"""

import os
from pathlib import Path

JOBS_PY = Path(
    "/var/lib/awx/venv/awx/lib64/python3.11/"
    "site-packages/awx/main/tasks/jobs.py"
)

if not JOBS_PY.exists():
    print(f"patch-jobs: {JOBS_PY} not found – skipping")
    raise SystemExit(0)

text = JOBS_PY.read_text()
original = text

# 1. Disable process isolation entirely for containerised deployments
text = text.replace(
    '"process_isolation": True',
    '"process_isolation": False',
    1,
)

# 2. Allow the executable to be overridden via env var (belt-and-braces)
text = text.replace(
    '"process_isolation_executable": "podman"',
    '"process_isolation_executable": os.getenv('
    '"ANSIBLE_RUNNER_PROCESS_ISOLATION_EXECUTABLE", "podman")',
    1,
)

if text != original:
    JOBS_PY.write_text(text)
    print("patch-jobs: patched jobs.py for containerised execution")
else:
    print("patch-jobs: no changes needed (already patched)")
