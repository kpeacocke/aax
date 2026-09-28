# Home infrastructure automation

This directory is the AWX project for the Raspberry Pi fleet, Synology NAS and
read-only discovery of the DrayTek network estate.

## Safety model

- The Pi-hole replica (`pi-harmony`) is patched first.
- The Pi-hole primary (`pi-terror`) is touched only after the replica's Pi-hole,
  Unbound, DNS port and recent Nebula Sync cycle all pass validation.
- `pi-mdns` has a separate playbook and schedule; it does not participate in
  the DNS-pair workflow. Its maintenance job also validates the production
  mDNS metrics endpoint, Avahi browse status, VLAN interfaces 1-4 and non-zero
  service visibility on each reflected VLAN.
  The endpoint follows the inventory address, and validation waits for an explicit
  Docker `healthy` state; a running container without a health check does not pass.
- A failure stops the workflow before the paired DNS host is touched.
- Reboots occur only when `/var/run/reboot-required` exists.
- Docker and the Portainer agent are reconciled and verified after each host.
- Host-key checking is enabled. Do not use passwords or private keys in Git.

Review the order in `inventories/home/hosts.yml` before the first production
run. Add `ansible_host` per host there only if local DNS names do not resolve
from the AWX execution container.

## Controller structure

Use repository and lifecycle boundaries, not device boundaries:

| AWX organization | AWX project | Repository | Scope |
| --- | --- | --- | --- |
| `Home Lab` | `AAX - Home Infrastructure` | `kpeacocke/aax` | Raspberry Pi fleet, Synology, network discovery and future DrayTek automation |
| `pi5-openclaw` | `pi-claw` | `kpeacocke/piclaw` | OpenClaw application lifecycle only |

Do not create a project per host or manufacturer. Within AAX, use inventory
groups and job-template prefixes as the operational boundary:

- `Discovery - *` is read-only and requires no device credential.
- `Raspberry Pi - *` operates on `raspberry_pi`, with `dns_pair` and `mdns`
  preserving their different failure and scheduling semantics.
- `Synology - *` operates on `synology` with a dedicated NAS credential.
- `DrayTek - <model family> - *` must remain model-specific once authenticated
  automation is introduced; do not combine heterogeneous CLI mutations.

Split AAX into another repository/project only when it gains a genuinely
independent release cycle, owner, security boundary, or reusable Ansible
collection. A new device alone is not a split criterion.

## AWX objects

Create these once in AWX:

1. Organization **Home Lab**. Keep application-specific projects such as
   `pi-claw` in their own organization.
2. Project **AAX - Home Infrastructure** pointed to this repository, branch
   `main`.
   Enable collection installation during project updates; AWX reads
   `collections/requirements.yml` and installs `community.docker`.
3. Inventory **Home Lab**, sourced from
   `automation/inventories/home/hosts.yml` when project inventory updates are
   supported by the execution environment. Otherwise mirror the Git groups in
   AWX and treat Git as the desired-state source.
4. A machine credential for the dedicated `ansible` account and its sudo
   password/key.
5. A custom credential that injects the secret as the extra variable
   `portainer_agent_secret`. It must equal the Portainer Server `AGENT_SECRET`.
6. Job template **Raspberry Pi - Audit** using
   `automation/playbooks/pi-audit.yml`.
7. Workflow **Raspberry Pi - DNS Pair Maintenance**, with concurrent jobs off:
   **DNS Replica Maintenance** uses the dedicated pi-harmony SSH credential and
   limit `pi-harmony`; its success edge starts **DNS Primary Maintenance**, using
   the dedicated pi-terror SSH credential and limit `pi-terror`. Both stages use
   `automation/playbooks/dns-pair-daily-maintenance.yml`, privilege escalation
   on, and concurrent jobs off. The primary stage retains the replica DNS and
   Nebula Sync gates. Schedule only the workflow at 03:00 Australia/Sydney;
   disable the superseded combined job's schedule before enabling this one.
8. Job template **Raspberry Pi - mDNS Maintenance** using
   `automation/playbooks/mdns-daily-maintenance.yml`, on a different daily
   schedule from the DNS pair. The job guards TCP/9105 before and after
   maintenance, requires the `avahi-reflector` container to remain healthy,
   then validates the exporter, Avahi browsing, VLAN interfaces 1-4 and
   non-zero advertisements on the service-producing VLANs (1, 3 and 4).
   VLAN 2 is a consumer network: zero local advertisements is valid, but its
   interface must remain up. Advertisement counts do not prove consumption.
   Verify discovery and connection to a known service from an actual VLAN 2
   client separately; the reflector's own browse is not a client-side test.
9. Job template **Raspberry Pi - Portainer Agents** using
   `automation/playbooks/portainer-agents.yml` for manual reconciliation.
10. Attach an AWX notification template to the **Error** event for the DNS
   workflow and the mDNS job template. Store the webhook/token in AWX, not this repository. The
   notification includes the failed job URL and the host/task that stopped the
   workflow.
11. Job template **Discovery - Network** using
    `automation/playbooks/network-discovery.yml`. It requires no device
    credential and only probes TCP/HTTP(S) from the execution environment.
12. Job template **Synology - Discovery** using
    `automation/playbooks/synology-discovery.yml`. Attach a dedicated Synology
    machine credential; do not use a personal DSM account. Start without
    privilege escalation. This job is read-only.
13. Optionally create **Discovery - Home Workflow** with **Discovery - Network**,
    **Raspberry Pi - Audit**, and **Synology - Discovery** as separate nodes.
    Keeping them separate allows each node to carry only the credential it
    needs and makes failures attributable.

## Raspberry Pi account bootstrap

The fleet audit and newly bootstrapped hosts use the AWX Machine credential
**Home Lab - Raspberry Pi Fleet** as user `ansible`, with its SSH private key
and `sudo` escalation. DNS workflow stages use the dedicated host credentials
listed above; mDNS uses **Home Lab - pi-mdns SSH**. Do not replace these with
the fleet credential until its key has been installed and verified on each host. The
matching public key is intentionally versioned in
`inventories/home/group_vars/raspberry_pi.yml`; private keys and passwords must
never be committed.

For a replacement host, create a temporary job template using
`playbooks/pi-bootstrap.yml` and a one-time administrative Machine credential.
Limit the first run to the replacement host. After it succeeds, delete the
temporary credential and verify the host with **Raspberry Pi - Audit** using the
permanent fleet credential. The role locks password authentication for the
`ansible` account, installs only the declared public key, and validates its
sudoers entry before replacing it.

Run **Pi - Audit** first. Run the DNS workflow and mDNS maintenance job manually
before enabling their daily schedules. Enable only the workflow schedule for
DNS; keep the superseded combined DNS job schedule disabled. Schedule the agent-only job after a deliberate
Portainer Server upgrade, not independently: Portainer requires agent and server
versions to match.

To change the Portainer pin, edit `portainer_server_version` in
`inventories/home/group_vars/raspberry_pi.yml`, merge the change, sync the AWX
project, then run **Pi - Portainer Agents**. Upgrade the Portainer Server first;
never advance only the agents.

## Discovery boundary

`network-discovery.yml` records which common TCP and HTTP(S) management
interfaces are reachable from the AWX execution container. It does not log in,
use stored device credentials, send configuration commands, or prove that a
reported firmware version is current. The version values in the inventory are
the operator-observed baseline and are reported for comparison.

`synology-discovery.yml` uses SSH to collect DSM release metadata, filesystem
capacity, Linux software-RAID state, installed packages, and Docker status. It
does not use `become`, modify DSM, inspect secrets, or export configuration.
Create a dedicated `awx-automation` DSM account and restrict it before attaching
its SSH key to the AWX template. DSM API and configuration-backup credentials
belong in later, separately approved templates.

## DrayTek boundary

DrayTek routers can expose a model-dependent SSH CLI and can be managed by
VigorACS. Do not apply generic CLI mutations to the gateway: command syntax and
transaction/rollback behavior vary by model and firmware.

The `draytek` inventory contains the known estate, grouped by operational role.
Do not attach the DrayTek usernames or passwords to the generic discovery job.
After reviewing its results, authenticated discovery and configuration backup
must be implemented per model family. Changes must use model-specific command
fixtures, pre/post connectivity tests, a one-device canary, and manual approval.
Prefer VigorACS for heterogeneous fleets where it is licensed and deployed.
