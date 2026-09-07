# Home infrastructure automation

This directory is an AWX project for the Raspberry Pi fleet and, once the exact
models and supported management interfaces are known, DrayTek equipment.

## Safety model

- Patching is rolling (`serial: 1`) and split into explicit waves.
- A failure stops the workflow before the next Pi is touched.
- Reboots occur only when `/var/run/reboot-required` exists.
- Docker and the Portainer agent are reconciled and verified after each host.
- `pi-mdns` is last because it is shared network infrastructure.
- Host-key checking is enabled. Do not use passwords or private keys in Git.

Review the order in `inventories/home/hosts.yml` before the first production
run. Add `ansible_host` per host there only if local DNS names do not resolve
from the AWX execution container.

## AWX objects

Create these once in AWX:

1. A source-control project pointed to this repository, branch `main`.
2. An inventory sourced from `automation/inventories/home/hosts.yml`.
3. A machine credential for the dedicated `ansible` account and its sudo
   password/key.
4. A custom credential that injects the secret as the extra variable
   `portainer_agent_secret`. It must equal the Portainer Server `AGENT_SECRET`.
5. Job template **Pi - Audit** using `automation/playbooks/pi-audit.yml`.
6. Job template **Pi - Daily Maintenance** using
   `automation/playbooks/pi-daily-maintenance.yml`, with concurrent jobs off,
   privilege escalation on, and a daily schedule in the local maintenance
   window.
7. Job template **Pi - Portainer Agents** using
   `automation/playbooks/portainer-agents.yml` for manual reconciliation.

Run **Pi - Audit** first. Run maintenance manually with one host per wave before
enabling its daily schedule. Schedule the agent-only job after a deliberate
Portainer Server upgrade, not independently: Portainer requires agent and server
versions to match.

## DrayTek boundary

DrayTek routers can expose a model-dependent SSH CLI and can be managed by
VigorACS. Do not apply generic CLI mutations to the gateway: command syntax and
transaction/rollback behavior vary by model and firmware.

The `draytek` inventory group intentionally contains no hosts. Before enabling
write automation, record each model, firmware release, management IP, SSH
availability, HA topology, and an out-of-band recovery path. The first AWX job
for each device must be a read-only facts/configuration backup. Changes should
then use model-specific command fixtures, pre/post connectivity tests, and a
manual approval workflow. Prefer VigorACS for heterogeneous fleets where it is
already licensed and deployed.
