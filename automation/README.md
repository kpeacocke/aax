# Home infrastructure automation

This directory is an AWX project for the Raspberry Pi fleet and, once the exact
models and supported management interfaces are known, DrayTek equipment.

## Safety model

- The Pi-hole replica (`pi-harmony`) is patched first.
- The Pi-hole primary (`pi-terror`) is touched only after the replica's Pi-hole,
  Unbound, DNS port and recent Nebula Sync cycle all pass validation.
- `pi-mdns` has a separate playbook and schedule; it does not participate in
  the DNS-pair workflow.
- A failure stops the workflow before the paired DNS host is touched.
- Reboots occur only when `/var/run/reboot-required` exists.
- Docker and the Portainer agent are reconciled and verified after each host.
- Host-key checking is enabled. Do not use passwords or private keys in Git.

Review the order in `inventories/home/hosts.yml` before the first production
run. Add `ansible_host` per host there only if local DNS names do not resolve
from the AWX execution container.

## AWX objects

Create these once in AWX:

1. A source-control project pointed to this repository, branch `main`.
   Enable collection installation during project updates; AWX reads
   `collections/requirements.yml` and installs `community.docker`.
2. An inventory sourced from `automation/inventories/home/hosts.yml`.
3. A machine credential for the dedicated `ansible` account and its sudo
   password/key.
4. A custom credential that injects the secret as the extra variable
   `portainer_agent_secret`. It must equal the Portainer Server `AGENT_SECRET`.
5. Job template **Pi - Audit** using `automation/playbooks/pi-audit.yml`.
6. Job template **Pi - DNS Pair Maintenance** using
   `automation/playbooks/dns-pair-daily-maintenance.yml`, with concurrent jobs
   off and privilege escalation on.
7. Job template **Pi - mDNS Maintenance** using
   `automation/playbooks/mdns-daily-maintenance.yml`, on a different daily
   schedule from the DNS pair.
8. Job template **Pi - Portainer Agents** using
   `automation/playbooks/portainer-agents.yml` for manual reconciliation.
9. Attach an AWX notification template to the **Error** event for both scheduled
   job templates. Store the webhook/token in AWX, not this repository. The
   notification includes the failed job URL and the host/task that stopped the
   workflow.

Run **Pi - Audit** first. Run both maintenance jobs manually before enabling
their daily schedules. Schedule the agent-only job after a deliberate
Portainer Server upgrade, not independently: Portainer requires agent and server
versions to match.

To change the Portainer pin, edit `portainer_server_version` in
`inventories/home/group_vars/raspberry_pi.yml`, merge the change, sync the AWX
project, then run **Pi - Portainer Agents**. Upgrade the Portainer Server first;
never advance only the agents.

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
