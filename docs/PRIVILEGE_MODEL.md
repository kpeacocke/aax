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

- No service mounts `/var/run/docker.sock`. The builder generates execution
  environment build contexts; image builds run on an isolated external host or CI runner.

Container hardening controls currently applied in compose:

- `security_opt: no-new-privileges:true` on non-database runtime services (builder/dev/tools/gateway/hub/eda paths).
- `cap_drop: [ALL]` on the same hardened service set.

## Kubernetes Privilege Notes

- `awx-task` and `awx-web` no longer mount host Docker socket.
- Receptor components run isolated in-cluster and do not require host socket mounts.
- `ee-builder` has no host socket or automatically mounted service account token.

## Building Execution Environments

Generate a context with `ansible-builder create --file execution-environment.yml
--output-filename Containerfile`. Copy the generated `context/` directory to a
dedicated build host or CI runner, then run `docker build -f context/Containerfile -t
<registry>/<image>:<tag> context/` there. Push the image to the registry and
configure the controller to use that image.

`ansible-builder build` inside the shipped builder no longer has access to a
container daemon. This is intentional: do not restore a host socket mount or
expose an unauthenticated remote daemon to make it work. Keep build workers
separate from platform/database hosts and restrict their registry credentials.

## Residual Risk and Mitigation

- Docker socket access implies host-level control if compromised; default manifests
  prohibit it, including in `ee-builder`.
- Restrict external build workers to trusted operators and isolate untrusted build inputs.
- Keep policy tests enabled to prevent accidental spread of socket mounts.

## Enforcement

Automated checks in `tests/test_repo_policy.py` verify:

- only approved services publish host ports
- localhost-first bind defaults
- no AWX task socket mount in Kubernetes
- no host Docker socket mounts in Compose or the Kubernetes builder
- latest-tag and weak-secret regressions
