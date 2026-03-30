# Privilege and Host-Control Model

This document tracks privileged runtime paths and residual host-control risk.

## Docker Compose Privilege Audit

Current services explicitly running as root (`user: "0"`):

- `awx-web`
- `awx-task`
- `awx-receptor`
- `receptor-hop`
- `receptor-execution`

Current Docker socket mount usage:

- `ee-builder` mounts `/var/run/docker.sock` to build execution environment images.

Container hardening controls currently applied in compose:

- `security_opt: no-new-privileges:true` on non-database runtime services (builder/dev/tools/gateway/hub/eda paths).
- `cap_drop: [ALL]` on the same hardened service set.

## Kubernetes Privilege Notes

- `awx-task` and `awx-web` no longer mount host Docker socket.
- Receptor components run isolated in-cluster and do not require host socket mounts.

## Residual Risk and Mitigation

- Docker socket access in `ee-builder` implies host-level control if compromised.
- Restrict `ee-builder` usage to trusted operators and isolated hosts.
- Prefer remote image-build services for stricter isolation in production-like environments.
- Keep policy tests enabled to prevent accidental spread of socket mounts.

## Enforcement

Automated checks in `tests/test_repo_policy.py` verify:

- only approved services publish host ports
- localhost-first bind defaults
- no AWX task socket mount in Kubernetes
- latest-tag and weak-secret regressions
