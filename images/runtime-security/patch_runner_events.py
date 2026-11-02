"""Remove the verified runner event-directory creation race."""

import ast
import importlib.util
from pathlib import Path


ORIGINAL = """        if not os.path.exists(job_events_path):
            os.mkdir(job_events_path, 0o700)
"""
REPLACEMENT = "        os.makedirs(job_events_path, mode=0o700, exist_ok=True)\n"


def patch(path: Path) -> None:
    source = path.read_text()
    if source.count(ORIGINAL) != 1:
        raise ValueError("Unexpected ansible-runner event-directory source; review upstream changes")
    updated = source.replace(ORIGINAL, REPLACEMENT)
    ast.parse(updated)
    path.write_text(updated)


if __name__ == "__main__":
    spec = importlib.util.find_spec("ansible_runner.runner")
    if spec is None or spec.origin is None:
        raise ValueError("Installed ansible-runner source is required")
    patch(Path(spec.origin))
