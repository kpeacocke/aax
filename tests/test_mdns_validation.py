"""Exercise the maintenance assertions against healthy and broken telemetry."""

import re
from pathlib import Path

from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAY = yaml.safe_load(
    (ROOT / "automation/playbooks/mdns-daily-maintenance.yml").read_text()
)[1]
ENV = Environment(undefined=StrictUndefined, autoescape=True)
ENV.filters["regex_search"] = lambda value, pattern: re.search(pattern, value)


def evaluate(expression, **variables):
    return ENV.compile_expression(expression)(**variables)


def test_container_requires_explicit_healthy_state():
    conditions = PLAY["tasks"][0]["until"]
    for state, expected in (
        ({"Running": True, "Health": {"Status": "healthy"}}, True),
        ({"Running": True}, False),
        ({"Running": True, "Health": {"Status": "starting"}}, False),
        ({"Running": True, "Health": {"Status": "unhealthy"}}, False),
        ({"Running": False, "Health": {"Status": "healthy"}}, False),
    ):
        result = {"exists": True, "container": {"State": state}}
        assert all(evaluate(c, mdns_container=result) for c in conditions) == expected
    missing = {"exists": False, "container": None}
    assert not all(evaluate(c, mdns_container=missing) for c in conditions)


def test_metrics_reject_zero_missing_and_malformed_values():
    tasks = {task["name"]: task for task in PLAY["tasks"]}
    service = tasks["Require each reflected VLAN to see at least one mDNS service"]
    interface = tasks["Require each reflected VLAN interface to be up"]
    for item in PLAY["vars"]["mdns_expected_interfaces"]:
        labels = ','.join(f'{key}="{item[key]}"' for key in ("interface", "vlan", "role"))
        for value, expected in (("1", True), ("12", True), ("0", False), ("-1", False), ("1garbage", False)):
            content = f'mdns_services_total{{{labels}}} {value}\n'
            assert bool(evaluate(service["ansible.builtin.assert"]["that"][0],
                                 mdns_metrics={"content": content}, item=item)) == expected
        for value, expected in (("1", True), ("0", False), ("10", False)):
            content = f'mdns_interface_up{{{labels}}} {value}\n'
            assert evaluate(interface["ansible.builtin.assert"]["that"][0],
                            mdns_metrics={"content": content}, item=item) == expected
        assert not evaluate(service["ansible.builtin.assert"]["that"][0],
                            mdns_metrics={"content": ""}, item=item)


def test_exporter_and_browse_require_exact_success_samples():
    task = next(t for t in PLAY["tasks"] if t["name"] == "Require exporter and Avahi browsing to be healthy")
    for metric, condition in zip(("mdns_exporter_up", "mdns_browse_success"), task["ansible.builtin.assert"]["that"]):
        for value, expected in (("1", True), ("0", False), ("10", False)):
            assert evaluate(condition, mdns_metrics={"content": f"{metric} {value}\n"}) == expected


if __name__ == "__main__":
    test_container_requires_explicit_healthy_state()
    test_metrics_reject_zero_missing_and_malformed_values()
    test_exporter_and_browse_require_exact_success_samples()
    print("All mDNS validation fixture tests passed")
