"""Regression tests for the EDA activation services and their Compose boundaries."""

import json
import os
from pathlib import Path
import secrets
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _compose_config() -> dict:
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_PASSWORD": secrets.token_urlsafe(32),
            "AWX_ADMIN_PASSWORD": secrets.token_urlsafe(32),
            "SECRET_KEY": secrets.token_urlsafe(32),
            "HUB_DB_PASSWORD": secrets.token_urlsafe(32),
            "HUB_ADMIN_PASSWORD": secrets.token_urlsafe(32),
            "GALAXY_SECRET_KEY": secrets.token_urlsafe(32),
            "PULP_SECRET_KEY": secrets.token_urlsafe(32),
            "EDA_DB_PASSWORD": secrets.token_urlsafe(32),
            "EDA_CONTROLLER_URL": "https://awx.ambitiouscake.com",
            "EDA_CONTROLLER_SSL_VERIFY": "true",
            "EDA_WEBSOCKET_BASE_URL": "wss://awx.ambitiouscake.com/eda/ws",
            "EDA_WEBSOCKET_SSL_VERIFY": "yes",
            "EDA_PODMAN_SOCKET_URL": "tcp://eda-podman:8888",
            "EDA_PODMAN_MEM_LIMIT": "512m",
            "EDA_PODMAN_DNS": "1.1.1.1",
        }
    )
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--profile",
            "controller",
            "--profile",
            "eda",
            "config",
            "--format",
            "json",
        ],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_activation_worker_uses_private_podman_and_secure_awx_url() -> None:
    services = _compose_config()["services"]
    worker = services["eda-activation-worker"]

    assert worker["command"] == ["activation-worker"]
    assert worker["environment"]["EDA_PODMAN_SOCKET_URL"] == "tcp://eda-podman:8888"
    assert worker["environment"]["EDA_PODMAN_MEM_LIMIT"] == "512m"
    assert worker["environment"]["EDA_CONTROLLER_URL"] == "https://awx.ambitiouscake.com"
    assert worker["environment"]["EDA_CONTROLLER_SSL_VERIFY"] == "true"
    assert worker["security_opt"] == ["no-new-privileges:true"]
    assert worker["cap_drop"] == ["ALL"]
    assert set(worker["networks"]) == {
        "awx-network",
        "eda-network",
        "eda-podman-network",
    }


def test_podman_api_is_private_and_storage_persists() -> None:
    config = _compose_config()
    podman = config["services"]["eda-podman"]

    assert podman["privileged"] is True
    assert "ports" not in podman
    assert set(podman["networks"]) == {"eda-podman-network"}
    assert any(
        mount["type"] == "volume"
        and mount["target"] == "/var/lib/containers/storage"
        and config["volumes"][mount["source"]]["name"] == "aax_eda_container_storage"
        for mount in podman["volumes"]
    )


def test_websocket_and_default_workers_keep_restricted_runtime_security() -> None:
    services = _compose_config()["services"]
    default_worker = services["eda-worker"]
    websocket = services["eda-ws"]

    assert default_worker["command"] == ["worker"]
    assert default_worker["security_opt"] == ["no-new-privileges:true"]
    assert default_worker["cap_drop"] == ["ALL"]
    assert websocket["command"] == ["ws"]
    assert websocket["environment"]["EDA_WORKER_KIND"] == "websocket"
    assert websocket["environment"]["EDA_WEBSOCKET_SSL_VERIFY"] == "yes"
    assert "ports" not in websocket


def test_public_eda_session_writes_have_an_explicit_trusted_origin() -> None:
    services = _compose_config()["services"]
    for name in ("eda-controller", "eda-worker", "eda-activation-worker", "eda-ws"):
        assert json.loads(services[name]["environment"]["EDA_CSRF_TRUSTED_ORIGINS"]) == [
            "https://awx.ambitiouscake.com"
        ]
