"""Evaluate real Ansible precedence without contacting or modifying a host."""

import os
from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_mdns_guards_survive_shared_defaults(tmp_path):
    source = ROOT / "automation/tasks/patch-wave.yml"
    play = yaml.safe_load(source.read_text())[0]
    # Preserve the real play's variables and imports, replacing every executable
    # task with local assertions so this test cannot perform maintenance.
    for key in ("pre_tasks", "tasks", "post_tasks", "handlers", "roles"):
        play.pop(key, None)
    play.update(gather_facts=False, become=False, connection="local")
    if "vars_files" in play:
        play["vars_files"] = [str((source.parent / p).resolve()) for p in play["vars_files"]]
    play["tasks"] = [{"ansible.builtin.assert": {"that": [
        "pi_guard_endpoints | length == 1",
        "pi_guard_endpoints[0].port == 9105",
        "pi_guard_endpoints[0].host == '192.168.5.101'",
        "pi_required_containers == ['avahi-reflector']",
        "pi_required_services == ['docker']",
        "pi_reconcile_portainer_agent == false",
    ]}}]
    safe_play = tmp_path / "safe-wave.yml"
    safe_play.write_text(yaml.safe_dump([play]))
    wrapper = yaml.safe_load((ROOT / "automation/playbooks/mdns-daily-maintenance.yml").read_text())[0]
    wrapper["ansible.builtin.import_playbook"] = str(safe_play)
    entry = tmp_path / "entry.yml"
    entry.write_text(yaml.safe_dump([wrapper]))
    result = subprocess.run(
        ["ansible-playbook", "-i", str(ROOT / "automation/inventories/home/hosts.yml"), str(entry)],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "ANSIBLE_LOCAL_TEMP": str(tmp_path / "ansible"), "ANSIBLE_NOCOLOR": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
