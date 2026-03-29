# AAP to AAX Component Mapping

This document provides a strict comparison between Red Hat Ansible Automation Platform (AAP) 2.6 and what AAX actually implements from upstream open-source projects.

It is intentionally conservative:

- `Mapped` means AAX includes an identifiable upstream project or service that covers the core role of the AAP component.
- `Partial` means AAX covers part of the role, but not the full AAP productized experience or not the full topology implied by AAP.
- `External` means AAX integrates with the capability but does not host it as part of the stack.
- `No equivalent` means there is no bundled AAX component that corresponds directly.
- `Commercial only` means the AAP capability depends on Red Hat productization, certification, support, or subscription rather than a standalone upstream project that AAX can bundle.

This is a mapping of platform components and upstream projects, not a claim of full AAP feature parity.

Source baseline:

- Red Hat AAP 2.6 Overview
- Current AAX Compose services in [docker-compose.yml](docker-compose.yml)
- Controller docs in [controller/CONTROLLER.md](controller/CONTROLLER.md)
- Hub docs in [hub/HUB.md](hub/HUB.md)
- EDA docs in [images/eda-controller/EDA.md](images/eda-controller/EDA.md)
- Architecture docs in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Executive Summary

For the major open-source building blocks of AAP, AAX has a credible mapping:

- Automation Controller maps to AWX
- Private Automation Hub maps to Galaxy NG plus Pulp
- Event-Driven Ansible maps to the bundled EDA controller stack
- Execution Environments map to the EE images and ansible-builder workflow
- Automation Mesh maps to Receptor

What AAX does not provide is the full AAP product surface:

- no Red Hat certified content service
- no separate Automation Gateway equivalent
- no supported installer/operator experience equivalent to AAP packaging
- no productized HA topology by default in Docker Compose
- no Red Hat support, lifecycle guarantees, or certified compatibility claims

## Strict Mapping Matrix

| AAP area | AAP component | AAX status | AAX implementation | Notes |
| --- | --- | --- | --- | --- |
| Core control plane | Automation Controller | Mapped | AWX (`awx-web`, `awx-task`, `awx-postgres`, `awx-redis`) | Core controller role is present: UI, API, jobs, inventories, credentials, workflows, RBAC. |
| Content platform | Private Automation Hub | Mapped | Galaxy NG + Pulp (`galaxy-ng`, `pulp-api`, `pulp-content`, `pulp-worker`, `hub-postgres`, `hub-redis`) | Core private content hosting and distribution role is present. |
| Event-driven automation | Event-Driven Ansible controller | Mapped | EDA controller stack (`eda-controller`, `eda-postgres`, `eda-redis`) | Bundled as a dedicated profile in Compose. |
| Execution runtime | Automation Execution Environments | Mapped | `ee-base`, `ee-builder`, `dev-tools` | Covers build and runtime model for containerized Ansible execution. |
| Distributed execution | Automation Mesh | Partial | Receptor (`awx-receptor`) | Receptor is present, but the default stack is a single-node deployment. Multi-node mesh exists as an extension pattern, not as a turnkey topology. |
| Community content source | Ansible Galaxy | External | Integration through Galaxy NG / Ansible Galaxy tooling | AAX does not host community Galaxy itself; it consumes it as an upstream source. |
| CLI/TUI content tooling | Automation Content Navigator | Mapped | ansible-navigator and ansible-lint in `dev-tools` | Present as tooling, not as a standalone service. |
| Data store | PostgreSQL | Mapped | `awx-postgres`, `hub-postgres`, `eda-postgres` | Present for controller, hub, and EDA. |
| Caching / broker | Redis | Mapped | `awx-redis`, `hub-redis`, `eda-redis` | Present for controller, hub, and EDA. |
| Certified partner / Red Hat content | Automation Hub certified content | Commercial only | None bundled | AAX cannot reproduce Red Hat certification and subscription-backed content. |
| Unified ingress / API front door | Automation Gateway | No equivalent | None bundled | AAX currently exposes component services directly or through external reverse proxying. |
| Default HA deployment model | High Availability Automation Hub / multi-node topology | Partial | Documented separately in [docs/HA-DEPLOYMENT.md](docs/HA-DEPLOYMENT.md) | HA is not the default Compose deployment. It requires external infrastructure or Kubernetes-style replication patterns. |
| Installer / operator experience | Productized AAP install and lifecycle tooling | No equivalent | None bundled | AAX uses Docker Compose and repo docs, not the AAP installer/operator packaging model. |
| Subscription / support / certification | Red Hat support lifecycle | Commercial only | None bundled | Outside the scope of an upstream-assembled project. |

## Upstream Project Inventory

This section answers the narrower question: do we have a complete mapping of the open-source projects that back AAX's AAP-like capabilities?

For the main platform building blocks, yes.

| Capability in AAX | Primary upstream project(s) | Where it appears in AAX |
| --- | --- | --- |
| Automation Controller | AWX | [controller/CONTROLLER.md](controller/CONTROLLER.md), [docker-compose.yml](docker-compose.yml) |
| Private Automation Hub UI / API | Galaxy NG | [hub/HUB.md](hub/HUB.md), [docker-compose.yml](docker-compose.yml) |
| Private Automation Hub content backend | Pulp | [hub/HUB.md](hub/HUB.md), [docker-compose.yml](docker-compose.yml) |
| Event-driven automation engine | ansible-rulebook / EDA controller stack | [images/eda-controller/EDA.md](images/eda-controller/EDA.md), [docker-compose.yml](docker-compose.yml) |
| Distributed execution / mesh | Receptor | [controller/CONTROLLER.md](controller/CONTROLLER.md), [docker-compose.yml](docker-compose.yml) |
| Execution environment build pipeline | ansible-builder | `ee-builder`, [README.md](README.md) |
| Execution environment runtime | ansible-core plus EE images | `ee-base`, `dev-tools`, controller defaults |
| Content CLI / TUI | ansible-navigator, ansible-lint | `dev-tools` |
| Datastores | PostgreSQL, Redis | controller, hub, and EDA backing services |

What is not represented as an upstream project mapping is the commercial and productized layer around AAP:

- certified content program
- Red Hat support and lifecycle guarantees
- bundled gateway model
- enterprise installer/operator packaging
- tested support matrix claims across all components

## Detailed Comparison

### 1. Automation Controller

`Mapped`

AAX uses AWX for the controller role. That is the correct upstream anchor for the AAP controller experience.

Included capabilities:

- web UI
- REST API
- projects and SCM sync
- inventories and credentials
- workflows and job templates
- RBAC
- execution history

Current AAX services:

- `awx-web`
- `awx-task`
- `awx-postgres`
- `awx-redis`

What is still different from AAP:

- supportability and lifecycle guarantees
- productized HA deployment model
- packaged upgrade path and tested support matrix

### 2. Private Automation Hub

`Mapped`

AAX uses Galaxy NG plus Pulp for the private hub role. That is the correct upstream composition for the open-source side of AAP hub functionality.

Included capabilities:

- collection hosting
- content API and UI
- Pulp-backed storage and metadata
- execution environment registry workflows
- approval/signing related configuration hooks

Current AAX services:

- `galaxy-ng`
- `pulp-api`
- `pulp-content`
- `pulp-worker`
- `hub-postgres`
- `hub-redis`

What is not equivalent to AAP:

- Red Hat certified content catalog
- Red Hat subscription-backed synchronization rights and support model
- turnkey HA topology by default

### 3. Event-Driven Ansible

`Mapped`

The EDA controller is present in AAX and documented in [images/eda-controller/EDA.md](images/eda-controller/EDA.md). This is not “coming soon” anymore and should be treated as implemented in the comparison.

Current AAX services:

- `eda-controller`
- `eda-postgres`
- `eda-redis`

Included capabilities:

- webhook ingestion
- rulebook processing
- event-driven action execution
- controller integration patterns

### 4. Execution Environments

`Mapped`

AAX has a clear execution-environment model:

- `ee-base` for default runtime
- `ee-builder` for building custom execution environments
- `dev-tools` for local content tooling

This is a good open-source mapping to the AAP EE concept.

### 5. Automation Mesh

`Partial`

Receptor is included, so the upstream project mapping exists. The reason this is `Partial` rather than `Mapped` is that the default AAX deployment is not a multi-node mesh topology out of the box.

What exists:

- Receptor service bundled with controller
- receptor configuration and exposed port
- documented path to extend with additional nodes

What is not turnkey:

- multi-node mesh deployment baked into the default Compose stack
- productized operational model for large-scale mesh rollout

### 6. High Availability

`Partial`

The repo contains HA guidance in [docs/HA-DEPLOYMENT.md](docs/HA-DEPLOYMENT.md), but the default stack is still single-node Docker Compose. That means HA is a deployment pattern supported by docs, not a bundled default architecture.

### 7. Automation Gateway

`No equivalent`

There is no separate gateway service or upstream gateway project bundled in AAX. If a unified ingress or API front door is required, it needs to be provided externally with a reverse proxy or additional infrastructure.

### 8. Certified Content

`Commercial only`

This is the sharpest boundary between AAX and AAP. AAX can host private content, but it cannot reproduce Red Hat-certified content distribution, certification status, or support guarantees.

## What AAX Can Reasonably Claim

AAX can reasonably claim:

- it assembles the major upstream open-source projects that correspond to the visible AAP building blocks
- it provides a usable controller, private hub, EDA, EE, and Receptor-based stack
- it documents HA and extension paths beyond the default Compose deployment

AAX should not claim:

- full AAP equivalence
- Red Hat certified content equivalence
- full productized HA parity out of the box
- Red Hat support, certification, or lifecycle compatibility

## Documentation Corrections Applied

This document corrects a few problems that existed in the older comparison:

- EDA is treated as implemented, not “coming soon”
- PostgreSQL coverage includes the EDA database as well as controller and hub databases
- Automation Mesh is described more carefully as present but not fully turnkey in the default topology
- AAP product-level differences are separated from upstream project mappings

## References

- [README.md](README.md)
- [docker-compose.yml](docker-compose.yml)
- [controller/CONTROLLER.md](controller/CONTROLLER.md)
- [hub/HUB.md](hub/HUB.md)
- [images/eda-controller/EDA.md](images/eda-controller/EDA.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/HA-DEPLOYMENT.md](docs/HA-DEPLOYMENT.md)

Last updated: March 29, 2026
