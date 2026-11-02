"""Verify the guarded patch and every maintained AWX interpreter consumer."""

from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATCH = runpy.run_path(str(ROOT / "images/runtime-security/patch_runner_events.py"))


@pytest.mark.parametrize("occurrences", [0, 1, 2])
def test_runner_patch_rejects_unknown_source(tmp_path: Path, occurrences: int) -> None:
    path = tmp_path / "runner.py"
    source = "import os\nclass Runner:\n    def run(self):\n        pass\n" + PATCH["ORIGINAL"] * occurrences
    path.write_text(source)
    if occurrences == 1:
        PATCH["patch"](path)
        assert PATCH["REPLACEMENT"] in path.read_text()
        assert PATCH["ORIGINAL"] not in path.read_text()
        with pytest.raises(ValueError, match="Unexpected ansible-runner"):
            PATCH["patch"](path)
    else:
        with pytest.raises(ValueError, match="Unexpected ansible-runner"):
            PATCH["patch"](path)
        assert path.read_text() == source


def test_runner_patch_is_applied_after_all_upstream_installs() -> None:
    for selector in ("Makefile", ".github/workflows/ci.yml"):
        assert "tests/test_runner_events.py" in (ROOT / selector).read_text()
    script = (ROOT / "scripts/patch-bundle-image.sh").read_text()
    stage = script.index('docker tag "$name:patched" "$name:devel"')
    suffix = script[stage:]
    assert "'awx /var/lib/awx/venv/awx/bin/python'" in suffix
    assert "'awx /usr/bin/python3.12'" not in suffix
    assert "'awx-ee /usr/bin/python3.12'" in suffix
    assert '[[ "$service" == "$name" ]] || continue' in suffix
    assert "-f images/runtime-security/Runner.Dockerfile" in suffix
    assert 'docker tag "$name:runner-patched" "$name:devel"' in suffix
    dockerfile = (ROOT / "images/runtime-security/Runner.Dockerfile").read_text()
    assert '"${PYTHON}" /tmp/patch_runner_events.py' in dockerfile
    assert '"${PYTHON}" /tmp/test_runner_events.py' in dockerfile
    assert dockerfile.index("USER root") < dockerfile.index("RUN") < dockerfile.index("USER 1000")


def test_runner_patch_rejects_invalid_syntax_without_writing(tmp_path: Path) -> None:
    path = tmp_path / "runner.py"
    source = "invalid Python !\n" + PATCH["ORIGINAL"]
    path.write_text(source)
    with pytest.raises(SyntaxError):
        PATCH["patch"](path)
    assert path.read_text() == source
