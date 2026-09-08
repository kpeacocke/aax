"""Policy tests for the home infrastructure inventory and discovery jobs."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _yaml(relative_path: str) -> dict:
    return yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def test_home_inventory_contains_declared_infrastructure() -> None:
    inventory = _yaml("automation/inventories/home/hosts.yml")
    children = inventory["all"]["children"]

    alexandria = children["synology"]["hosts"]["alexandria"]
    assert alexandria["ansible_host"] == "192.168.48.1"
    assert alexandria["management_address"] == "192.168.5.100"

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
    content = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "automation/playbooks/network-discovery.yml",
            "automation/tasks/discover-device.yml",
        )
    )
    assert "connection: local" in content
    assert "ansible.builtin.wait_for" in content
    assert "ansible.builtin.uri" in content
    assert "password" not in content.lower()
    assert "become: true" not in content


def test_git_managed_discovery_catalog_matches_network_inventory() -> None:
    inventory = _yaml("automation/inventories/home/hosts.yml")
    devices = _yaml("automation/vars/home_devices.yml")["home_network_devices"]
    children = inventory["all"]["children"]
    inventory_names = {"alexandria"}
    inventory_names.update(
        host
        for group in children["draytek"]["children"].values()
        for host in group.get("hosts", {})
    )
    assert {device["name"] for device in devices} == inventory_names


def test_inventory_does_not_commit_device_usernames_or_passwords() -> None:
    content = (REPO_ROOT / "automation/inventories/home/hosts.yml").read_text(
        encoding="utf-8"
    )
    for forbidden in ("bigman", "kpeacocke", "ansible_password", "api_key"):
        assert forbidden not in content


def test_controller_object_model_has_clear_repository_boundaries() -> None:
    model = _yaml("automation/controller/object-model.yml")

    aax_project = model["projects"][0]
    assert aax_project["organization"] == "Home Lab"
    assert aax_project["scm_url"] == "https://github.com/kpeacocke/aax.git"
    assert aax_project["scm_branch"] == "main"

    template_names = [item["name"] for item in model["job_templates"]]
    assert len(template_names) == len(set(template_names))
    assert all(
        item["project"] == "AAX - Home Infrastructure"
        and item["inventory"] == "Home Lab"
        for item in model["job_templates"]
    )

    assert model["external_projects"] == [
        {
            "name": "pi-claw",
            "organization": "pi5-openclaw",
            "repository": "https://github.com/kpeacocke/piclaw",
            "rationale": "Separate application repository and release lifecycle",
        }
    ]
