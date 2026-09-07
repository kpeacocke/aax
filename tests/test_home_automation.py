"""Policy tests for the home infrastructure inventory and discovery jobs."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _yaml(relative_path: str) -> dict:
    return yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_home_inventory_contains_declared_infrastructure() -> None:
    inventory = _yaml("automation/inventories/home/hosts.yml")
    children = inventory["all"]["children"]

    assert children["synology"]["hosts"]["alexandria"]["ansible_host"] == "192.168.5.100"

    draytek_children = children["draytek"]["children"]
    draytek_hosts = {
        host
        for group in draytek_children.values()
        for host in group.get("hosts", {})
    }
    assert draytek_hosts == {
        "HomeOne",
        "MilSwitch",
        "KPOffice",
        "KPShelf",
        "TVRoom",
        "KidsRoom",
        "KidsMesh",
        "OfficeMesh",
    }


def test_discovery_playbook_has_no_mutating_or_secret_inputs() -> None:
    content = (REPO_ROOT / "automation/playbooks/network-discovery.yml").read_text(
        encoding="utf-8"
    )
    assert "connection: local" in content
    assert "ansible.builtin.wait_for" in content
    assert "ansible.builtin.uri" in content
    assert "password" not in content.lower()
    assert "become: true" not in content


def test_inventory_does_not_commit_device_usernames_or_passwords() -> None:
    content = (REPO_ROOT / "automation/inventories/home/hosts.yml").read_text(
        encoding="utf-8"
    )
    for forbidden in ("bigman", "kpeacocke", "ansible_password", "api_key"):
        assert forbidden not in content
