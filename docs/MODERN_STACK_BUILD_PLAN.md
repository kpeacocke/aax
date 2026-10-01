# Modern AAP-like Build Plan

This plan defines the correct modern upstream component mapping for the AAP-like stack in this repository.

## 1. Upstream component mapping

| AAP capability                           | Upstream project                                | Role in the stack                         | Build responsibility                                                    |
| ---------------------------------------- | ----------------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| Controller / UI / API                    | AWX                                             | Core automation control plane             | Consume upstream release; do not fork the controller code               |
| Execution environments                   | ansible-builder + ansible-runner + AWX EE model | Job runtime and execution image packaging | Build repo-owned EE images for compatibility                            |
| Private automation hub                   | Galaxy NG + Pulp                                | Collection and content distribution       | Consume upstream content platform; keep it pinned to supported versions |
| Automation mesh                          | Receptor                                        | Execution mesh / agent communication      | Consume upstream mesh runtime                                           |
| Event-driven automation                  | ansible-rulebook                                | Event-triggered automation                | Consume upstream EDA runtime                                            |
| Content discovery / collection ecosystem | Ansible Galaxy / Galaxy NG                      | Collection publication and retrieval      | Run via upstream Galaxy NG + Pulp                                       |

The important design decision is simple: do not rebuild AWX itself from source. Build the compatibility layer that makes the upstream stack work as a coherent deployment.

## 2. Build strategy

### 2.1 Upstream runtime foundation

The repo should treat the following as upstream dependencies:

- AWX
- AWX EE
- Galaxy NG
- Pulp
- Receptor
- ansible-rulebook
- ansible-builder / ansible-runner

These should be pinned to a tested baseline and kept in sync with one another.

### 2.2 Repo-owned compatibility layer

This repository should own the custom compatibility assets that are not upstream projects:

- `ee-base`
- `ee-builder`
- `dev-tools`
- gateway configuration
- networking and hostname policy
- secret handling and security defaults
- Portainer stack glue and deployment workflow
- smoke-test and validation scripts

This is the part that should be built and published by the repo.

## 3. Current baseline target

The repo currently demonstrates a rolling upstream development baseline:

- AWX `devel`
- AWX EE `devel`
- Receptor `devel`

This is the starting point for the modern build plan; image builds should be validated together because these upstream branches move independently.

## 4. Release policy

The modern plan requires the stack to operate as a versioned bundle instead of a floating `latest` stream.

### Required policy

- Each upstream component version must be tested together.
- The stack must ship as a bundle with one compatibility tag.
- The repo-owned compatibility images must be published with explicit semver or tested-stack tags.
- Portainer must deploy exact tags, never implicit `latest` in controlled production environments.

### Prohibited pattern

- no implicit `AAX_VERSION=latest` in production-facing deployments
- no unreviewed version drift across controller, hub, and mesh components
- no treating the whole stack as a moving target without validation

## 5. Portainer deployment flow

The deployment flow should be:

1. Define the stack version in a single matrix document.
2. Validate the upstream component set in CI.
3. Build and publish repo-owned compatibility images.
4. Pin the deployed stack in Portainer to the tested tag set.
5. Redeploy by exact tag, not `latest`.
6. Run smoke validation after every release.

This keeps Portainer as the orchestration layer while the repo serves as the versioned source of truth.

## 6. Build phases

### Phase 1: lock the baseline

- finalize the upstream version set
- document compatibility matrix
- pin secret, network, and profile defaults

### Phase 2: build the compatibility layer

- build `ee-base`, `ee-builder`, and `dev-tools`
- build the gateway and support images
- test them against the upstream runtime set

### Phase 3: release the stack bundle

- publish repo-owned images to GHCR using explicit tags
- publish a release doc showing the tested bundle
- keep Portainer deployments pinned to the bundle tag

### Phase 4: maintain the stack

- update upstream components deliberately
- validate after each compatibility bump
- keep a changelog per stack release

## 7. Exit criteria for a modern release

A release is modern and defensible when all of the following are true:

- upstream components are version-pinned and compatible
- repo-owned compatibility images are versioned and tested
- Portainer deploys exact tags, not implicit `latest`
- smoke tests validate the full stack
- the stack is documented as a tested bundle, not a floating lab configuration

## 8. Recommendation

The right model for this repository is not a fork of AWX. It is a modern compatibility stack around supported upstream projects, with repo-owned custom images and Portainer-based orchestration.

That is the correct AAP-like architecture for a self-hosted stack in 2026.
