# Modern AAP-like Stack Strategy

This project is intentionally structured as a modern, compatible AAP-like deployment stack rather than a source-fork of upstream AWX.

## Goal

Keep the stack aligned to a recent, supported upstream baseline while retaining a repo-owned compatibility layer for local operations, networking, security defaults, and deployment orchestration.

## Architecture model

### Upstream runtime foundation

The stack relies on upstream-maintained components for the core platform runtime:

- AWX
- AWX EE
- Galaxy NG / Pulp
- EDA components
- Receptor

These are treated as upstream dependencies and remain version-pinned to a tested baseline rather than floating on `latest`.

### Repo-owned compatibility layer

This repository owns the glue that makes the upstream pieces work as a coherent self-hosted stack:

- execution environment customization
- gateway and reverse-proxy setup
- network boundary defaults
- secret handling and guardrails
- deployment docs and runtime validation
- Portainer-oriented stack behavior

This layer is where the project adds value.

## Release posture

The stack should follow a modern release posture:

1. Test exact upstream component versions together.
2. Validate compatibility with the repo-owned images.
3. Publish repo-owned compatibility artifacts from a controlled CI path.
4. Deploy the assembled stack through Portainer from a tracked repository state.
5. Only change versions intentionally after smoke validation.

## Why this is the right model

This avoids two bad extremes:

- building a full AWX fork from source for no practical gain
- drifting on unstable `latest` channels with no explicit compatibility contract

It preserves a current, maintainable stack while keeping the repo focused on operational compatibility rather than reinventing upstream software.

## Portainer role

Portainer remains the deployment control plane. The repo provides the stack definition and operational defaults; Portainer performs pull/redeploy operations in the target environment.

This is a good fit for a self-hosted deployment model because it separates:

- application definition and versioning in Git
- runtime orchestration in Portainer
- local validation in CI and developer tooling

## Current baseline

The repo currently targets a recent tested baseline with explicit version pins, including:

- AWX `24.6.1`
- AWX EE `24.6.1`
- Receptor `v1.6.4`

The goal is to keep this baseline current and compatible, while making the repo-owned compatibility layer deliberate and supportable.
