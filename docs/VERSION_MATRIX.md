# Tested Version Matrix

This document is the canonical tested version matrix for the current AAX baseline.

## Compose and Portainer Component Images

| Component      | Default Tag | Source                          |
| -------------- | ----------- | ------------------------------- |
| awx            | `24.6.1`    | `AWX_VERSION`                   |
| awx-ee         | `24.6.1`    | `AWX_EE_VERSION`                |
| ee-base        | `latest`    | `AAX_VERSION`                   |
| ee-builder     | `latest`    | `AAX_VERSION`                   |
| dev-tools      | `latest`    | `AAX_VERSION`                   |
| galaxy-ng      | `latest`    | `AAX_VERSION`                   |
| pulp           | `latest`    | `AAX_VERSION`                   |
| eda-controller | `latest`    | `AAX_VERSION`                   |
| gateway        | `latest`    | `AAX_VERSION`                   |
| receptor       | `v1.6.4`    | `RECEPTOR_VERSION`              |

## Kubernetes Component Images

The Kubernetes manifests remain pinned to the locally built `aax/*:1.0.0`
baseline. They do not follow the Compose/Portainer `AAX_VERSION` channel and
must be advanced deliberately as a separate deployment target.

## Runtime Base Dependencies

| Dependency            | Default channel                         |
| --------------------- | --------------------------------------- |
| PostgreSQL (AWX, EDA) | `15` (floats to the newest `15.x`)      |
| PostgreSQL (Hub)      | `16-alpine` (newest Alpine `16.x`)      |
| Redis                 | `7.4` / `7.4-alpine` (newest `7.4.x`) |

## Update Rules

- Update this file whenever changing default image tags in Compose, Kubernetes,
  or `.env.example`.
- Keep CI/release workflows aligned with these defaults.
- Run policy and docs contract tests after any version change.

## Digest Pinning Strategy

- Use immutable digest pinning for externally sourced base/runtime images where practical.
- Use Portainer's `AAX_VERSION` as the deployment gate. The lab tracks the
  tested `latest` main-branch build until a semantic release tag is available.
- PostgreSQL and Redis intentionally use upstream-maintained floating channels.
  Watchtower is label-enabled but monitor-only for these stateful services: it
  reports a changed digest and Portainer remains the manual deployment gate.
- AWX, AWX EE, and Receptor use exact versions because their upgrades require
  coordinated compatibility testing. AAX uses the controlled `latest` channel
  for the lab and semantic tags for immutable releases.
- Introduce digest enforcement incrementally after validating multi-arch release behavior.
