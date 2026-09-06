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

| Dependency            | Default          |
| --------------------- | ---------------- |
| PostgreSQL (AWX, EDA) | `15.14`              |
| PostgreSQL (Hub)      | `16.10-alpine`       |
| Redis                 | `7.4.5` / `7.4.5-alpine` |

## Update Rules

- Update this file whenever changing default image tags in compose, k8s, or `.env.example`.
- Keep CI/release workflows aligned with these defaults.
- Run policy and docs contract tests after any version change.

## Digest Pinning Strategy

- Use immutable digest pinning for externally sourced base/runtime images where practical.
- Keep local project image tags pinned to tested release versions through
  Portainer's `AAX_VERSION` variable.
- Watchtower can detect a changed digest behind the selected tag; it cannot
  discover a new semantic tag. Dependabot PRs are the version-update signal.
- Introduce digest enforcement incrementally after validating multi-arch release behavior.
