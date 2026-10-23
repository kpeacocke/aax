import base64
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hub_entrypoint", ROOT / "images/galaxy-runtime/entrypoint.py"
)
assert SPEC is not None and SPEC.loader is not None
ENTRYPOINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRYPOINT)


def test_key_is_private_valid_and_survives_redeploy(tmp_path: Path) -> None:
    key = tmp_path / "certs" / "database_fields.symmetric.key"
    ENTRYPOINT.initialize_key(key)
    original = key.read_bytes()
    assert len(base64.b64decode(original, altchars=b"-_", validate=True)) == 32
    assert key.stat().st_mode & 0o777 == 0o600
    ENTRYPOINT.initialize_key(key)
    assert key.read_bytes() == original


def test_concurrent_roles_share_one_complete_key(tmp_path: Path) -> None:
    key = tmp_path / "certs" / "database_fields.symmetric.key"
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: ENTRYPOINT.initialize_key(key), range(32)))
    assert len(base64.b64decode(key.read_bytes(), altchars=b"-_", validate=True)) == 32
    assert sorted(path.name for path in key.parent.iterdir()) == [
        "database_fields.symmetric.key", "database_fields.symmetric.lock",
    ]


@pytest.mark.parametrize("contents", [b"", b"invalid", base64.urlsafe_b64encode(b"short")])
def test_invalid_existing_key_fails_without_replacing_it(tmp_path: Path, contents: bytes) -> None:
    key = tmp_path / "database_fields.symmetric.key"
    key.write_bytes(contents)
    with pytest.raises(ValueError):
        ENTRYPOINT.initialize_key(key)
    assert key.read_bytes() == contents


def test_all_hub_roles_use_same_persistent_filesystem_and_key() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.devel.yml").read_text())
    for name in ("pulp-api", "pulp-content", "pulp-worker", "galaxy-ng"):
        service = compose["services"][name]
        assert service["environment"]["PULP_DEFAULT_FILE_STORAGE"] == "pulpcore.app.models.storage.FileSystem"
        assert service["environment"]["PULP_MEDIA_ROOT"] == "/var/lib/pulp/media"
        assert service["environment"]["PULP_REDIRECT_TO_OBJECT_STORAGE"] == "false"
        assert service["environment"]["PULP_DB_ENCRYPTION_KEY"] == "/etc/pulp/certs/database_fields.symmetric.key"
        assert "hub_pulp_certs:/etc/pulp/certs" in service["volumes"]
