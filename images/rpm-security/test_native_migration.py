import io
from pathlib import Path
import subprocess
import tarfile

import pytest


ROOT = Path(__file__).parent


@pytest.mark.parametrize("legacy", [False, True])
def test_podman_source_archive_rejects_retired_docker(
    tmp_path: Path, legacy: bool
) -> None:
    module = "module github.com/containers/podman/v5\n"
    dependency = (
        "github.com/docker/docker v28.5.1+incompatible"
        if legacy
        else "github.com/moby/moby/api v1.54.2"
    )
    (tmp_path / "go.mod").write_text(module)
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as source:
        for name, content in {
            "go.mod": f"{module}\nrequire {dependency}\n",
            "go.sum": "",
            "vendor/modules.txt": f"# {dependency}\n",
        }.items():
            data = content.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            source.addfile(member, io.BytesIO(data))
    result = subprocess.run(
        ["bash", str(ROOT / "go-vendor.sh"), "unused.json", str(archive)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert (result.returncode == 0) is not legacy
    if legacy:
        assert "must not retain the retired" in result.stderr


def test_moby_backport_is_retained_in_srpm_and_build_context() -> None:
    prepare = (ROOT / "prepare.sh").read_text()
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "Patch9995: aax-podman-moby-api.patch" in prepare
    assert "cp /aax/podman-moby-api.patch" in prepare
    assert "podman-moby-api.patch /aax/" in dockerfile
    patch = (ROOT / "podman-moby-api.patch").read_text()
    assert "+\t\"github.com/docker/docker/" not in patch
    assert "libpod/namesgenerator/names-generator_test.go" in patch
    assert "github.com/moby/moby/api/types/jsonstream" in patch
    assert "cmd/podman-testing/store_supported.go" in patch
    assert "Source9994: aax-dnsname-vendor.tar.gz" in prepare
    assert "bash %{SOURCE9999} %{SOURCE9998} %{SOURCE9994}" in prepare
