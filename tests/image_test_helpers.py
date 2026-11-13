"""Shared helpers for checking image versions against their pinned inputs."""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def pinned_version(requirements_path: Path, package: str) -> str:
    prefix = f"{package}=="
    for line in requirements_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split("==", 1)[1]
    raise AssertionError(f"{package} is not pinned in {requirements_path}")


def ee_base_python_minor_version() -> str:
    dockerfile = (REPO_ROOT / "images/ee-base/Dockerfile").read_text(encoding="utf-8")
    match = re.search(r"^FROM python:(\d+\.\d+)", dockerfile, re.MULTILINE)
    if match is None:
        raise AssertionError("ee-base Dockerfile does not declare a Python base image")
    return match.group(1)
