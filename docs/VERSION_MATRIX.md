# Tested Version Matrix

This document is the canonical tested version matrix for the current AAX baseline.

## AAX Component Images

| Component      | Default Tag | Source                          |
| -------------- | ----------- | ------------------------------- |
| awx            | `24.6.1`    | `AWX_VERSION`                   |
| awx-ee         | `24.6.1`    | `AWX_EE_VERSION`                |
| ee-base        | `1.0.0`     | `AAX_VERSION`                   |
| ee-builder     | `1.0.0`     | `AAX_VERSION`                   |
| dev-tools      | `1.0.0`     | `AAX_VERSION`                   |
| galaxy-ng      | `1.0.0`     | compose + kustomize             |
| pulp           | `1.0.0`     | compose + kustomize             |
| eda-controller | `1.0.0`     | compose + kustomize             |
| gateway        | `1.0.0`     | compose + kustomize             |
| receptor       | `v1.6.4`    | `RECEPTOR_VERSION`              |

## Runtime Base Dependencies

| Dependency            | Default channel                         |
| --------------------- | --------------------------------------- |
| PostgreSQL (AWX, EDA) | `15` (floats to the newest `15.x`)      |
| PostgreSQL (Hub)      | `16-alpine` (newest Alpine `16.x`)      |
| Redis                 | `7.4` / `7.4-alpine` (newest `7.4.x`) |

## Update Rules

- Update this file whenever changing default image tags in compose, k8s, or `.env.example`.
- Keep CI/release workflows aligned with these defaults.
- Run policy and docs contract tests after any version change.

## Digest Pinning Strategy

- Use immutable digest pinning for externally sourced base/runtime images where practical.
- Keep local project image tags pinned to tested release versions through
  Portainer's `AAX_VERSION` variable.
- PostgreSQL and Redis intentionally use upstream-maintained floating channels.
  Watchtower is label-enabled but monitor-only for these stateful services: it
  reports a changed digest and Portainer remains the manual deployment gate.
- AWX, AWX EE, Receptor, and AAX use exact versions because verified floating
  tags are unavailable or upgrades require coordinated compatibility testing.
- Introduce digest enforcement incrementally after validating multi-arch release behavior.
