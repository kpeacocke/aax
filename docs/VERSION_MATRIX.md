# Tested Version Matrix

This document is the canonical tested version matrix for the current AAX baseline.

## AAX Component Images

| Component      | Default Tag | Source                          |
| -------------- | ----------- | ------------------------------- |
| awx            | `1.0.0`     | `AWX_IMAGE` / compose default   |
| ee-base        | `1.0.0`     | `VERSION` / compose + kustomize |
| ee-builder     | `1.0.0`     | `VERSION` / compose + kustomize |
| dev-tools      | `1.0.0`     | `VERSION` / compose + kustomize |
| galaxy-ng      | `1.0.0`     | compose + kustomize             |
| pulp           | `1.0.0`     | compose + kustomize             |
| eda-controller | `1.0.0`     | compose + kustomize             |
| gateway        | `1.0.0`     | compose + kustomize             |
| receptor       | `latest`    | `RECEPTOR_IMAGE`                |

## Runtime Base Dependencies

| Dependency            | Default          |
| --------------------- | ---------------- |
| PostgreSQL (AWX, EDA) | `15`             |
| PostgreSQL (Hub)      | `16-alpine`      |
| Redis                 | `7` / `7-alpine` |

## Update Rules

- Update this file whenever changing default image tags in compose, k8s, or `.env.example`.
- Keep CI/release workflows aligned with these defaults.
- Run policy and docs contract tests after any version change.

## Digest Pinning Strategy

- Use immutable digest pinning for externally sourced base/runtime images where practical.
- Keep local project image tags pinned to tested release versions.
- Introduce digest enforcement incrementally after validating multi-arch release behavior.
