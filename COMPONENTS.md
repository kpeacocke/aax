# Red Hat Ansible Automation Platform 2.6 Components

This document maps all official Red Hat Ansible Automation Platform (AAP) 2.6 components to their AAX implementation status, based on the [Red Hat AAP 2.6 Overview](https://docs.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.6/html/overview/index).

**Source:** Red Hat AAP 2.6 documentation, Chapter 3: Red Hat Ansible Automation Platform components

## Component Implementation Matrix

### ✅ Fully Implemented Components

#### 3.2. Automation Controller

- **Official Description:** Enterprise framework enabling users to define, operate, scale, and delegate Ansible automation across their enterprise.
- **AAX Implementation:** [AWX](https://github.com/ansible/awx) v24.6.1
- **Services:** awx-web, awx-task, awx-postgres, awx-redis
- **Features:**
  - Web UI and REST API for automation management
  - Job template creation and execution
  - Inventory management
  - Credential management
  - Role-based access control (RBAC)
  - Project synchronization (Git integration)
  - Workflow orchestration
  - Execution history and logging
- **Deployment:** Docker Compose (`docker-compose.yml`, `controller` profile)
- **Access:** `http://localhost:18080`

#### 3.3. Private Automation Hub

- **Official Description:** Provides both disconnected and on-premise solutions for synchronizing content. You can synchronize collections and execution environment images from Red Hat cloud automation hub, storing and serving your own custom automation collections and execution images.
- **AAX Implementation:** [Galaxy NG](https://github.com/ansible/galaxy_ng) v4.9.2 + [Pulp](https://github.com/pulpproject/pulp)
- **Services:** galaxy-ng, pulp-api, pulp-content, pulp-worker, hub-postgres, hub-redis
- **Features:**
  - Custom Ansible Collection hosting and distribution
  - Execution Environment (container) registry
  - Content versioning and lifecycle management
  - Integration with CI/CD pipelines
  - Support for multiple content sources
  - API for programmatic access
  - Web UI for content discovery
- **Deployment:** Docker Compose (`docker-compose.yml`, `hub` profile)
- **Access:** `http://localhost:15001`
- **Content Sources:** Can pull from galaxy.ansible.com, GitHub, or other registries

#### 3.6. Automation Mesh

- **Official Description:** Overlay network intended to ease the distribution of work across a large and dispersed collection of workers through nodes that establish peer-to-peer connections with each other using existing networks.
- **AAX Implementation:** [Receptor](https://github.com/ansible/receptor)
- **Features:**
  - Peer-to-peer mesh networking
  - Dynamic cluster capacity scaling
  - Control and execution plane separation
  - Distribution of automation workloads
  - Resilient routing with outage recovery
  - Multi-hop mesh communication
  - FIPS-compliant encryption
- **Deployment:** Docker Compose (integrated with controller stack)
- **Use Cases:** Distributed execution across multiple execution nodes/environments

#### 3.7. Automation Execution Environments

- **Official Description:** Container images on which all automation in Red Hat Ansible Automation Platform is run. They provide a solution that includes the Ansible execution engine and hundreds of modules.
- **AAX Implementation:** [Ansible](https://github.com/ansible/ansible) + [ansible-builder](https://github.com/ansible/ansible-builder) v3.1.0
- **Execution Environments:**
  - **ee-base:** Base EE with Ansible Core 2.20.0, Python 3.14, standard modules
  - **ee-builder:** Extends ee-base with ansible-builder for building custom EEs
  - **dev-tools:** Extends ee-base with development and testing tools (ansible-navigator, ansible-lint)
- **Features:**
  - Consistent, reproducible automation environment
  - Pre-built with common modules and dependencies
  - Customizable via ansible-builder for specific requirements
  - Containerized execution
  - Support for multiple Python versions
- **Deployment:** Docker Compose (used by controller and locally)
- **Building Custom EEs:** Use `ee-builder` or [ansible-builder](https://github.com/ansible/ansible-builder) directly

#### 3.8. Ansible Galaxy (Community Content Source)

- **Official Description:** A hub for finding, reusing, and sharing Ansible content. Community-provided Galaxy content, in the form of prepackaged roles, can help start automation projects.
- **AAX Implementation:** Content source integration
- **Features:**
  - Private Automation Hub can pull collections from galaxy.ansible.com
  - Support for community roles and modules
  - Ansible Galaxy CLI integration
  - Content discovery and reuse
- **Deployment:** Not hosted in AAX; used as external content source
- **Integration:** Collections can be published to Private Automation Hub from local sources or galaxy.ansible.com

#### 3.9. Automation Content Navigator

- **Official Description:** A textual user interface (TUI) that becomes the primary command line interface into the automation platform, covering use cases from content building, running automation locally in an execution environment, running automation in Ansible Automation Platform.
- **AAX Implementation:** [Ansible Navigator](https://github.com/ansible/ansible-navigator) v24.2.0 + [ansible-lint](https://github.com/ansible/ansible-lint) v25.12.1
- **Included in:** `dev-tools` execution environment
- **Features:**
  - TUI for exploring execution environment contents
  - Running playbooks locally in EE
  - Collection documentation browsing
  - Playbook linting and validation (ansible-lint)
  - Content building support
- **Deployment:** Docker Compose (dev-tools service)
- **Usage:** `docker compose exec dev-tools ansible-navigator`

#### 3.10. PostgreSQL

- **Official Description:** Open-source relational database management system. For Ansible Automation Platform, Postgres serves as the backend database to store automation data such as job templates, inventory, credentials, and execution history.
- **AAX Implementation:** PostgreSQL 15
- **Instances:**
  - `awx-postgres` - Backend for Automation Controller
  - `hub-postgres` - Backend for Private Automation Hub
- **Features:**
  - Persistent data storage for jobs, inventories, credentials
  - User authentication and RBAC data
  - Execution history and logging
  - High availability support (external load balancer required)
- **Deployment:** Docker Compose (separate containers, persistent volumes)

---

### ⚠️ Partially Implemented Components

#### 3.4. High Availability Automation Hub

- **Official Description:** Multiple nodes that concurrently run the same service with a load balancer distributing workload (active-active configuration). This configuration eliminates single points of failure.
- **AAX Implementation:** Single-node Docker Compose (HA requires external infrastructure)
- **Current Limitation:** Single Private Automation Hub instance
- **HA Requirements for Production:**
  - External load balancer (e.g., HAProxy, nginx, cloud provider LB)
  - Multiple PostgreSQL replicas with streaming replication
  - Multiple Pulp worker instances
  - Shared storage for content (distributed filesystem or S3-compatible storage)
  - Redis cluster for distributed caching
- **Planned:** Kubernetes deployment (k8s/) includes HA support via multiple replicas
- **Recommendation:** For HA, deploy to Kubernetes or add external load balancer to Docker Compose setup

---

### ✅ Fully Implemented Components (Continued)

#### 3.5. Event-Driven Ansible Controller

- **Official Description:** The interface for event-driven automation and introduces automated resolution of IT requests. Helps you connect to sources of events and act on those events by using rulebooks.
- **AAX Implementation:** [ansible-rulebook](https://github.com/ansible/ansible-rulebook) v1.1.3
- **Services:** eda-controller, eda-postgres, eda-redis
- **Features:**
  - Event source integration (webhooks, monitoring systems, message queues)
  - Rulebook execution and management via REST API
  - Event processing and decision automation
  - Integration with Automation Controller for direct job triggering
  - Scalable event handling via Redis message queue
  - Event history and logging
  - Webhook endpoint for external event submission
  - Real-time event streaming via WebSocket
- **Deployment:** Docker Compose (`docker-compose.yml`, `eda` profile)
- **Access:** REST API on `http://localhost:15000`
- **Documentation:** [images/eda-controller/EDA.md](./images/eda-controller/EDA.md) with rulebook examples and AWX integration patterns

---

### ❌ Not Implemented / Out of Scope

#### 3.1. Ansible Automation Hub (Red Hat Certified Content)

- **Official Description:** Repository for certified content of Ansible Content Collections. Centralized repository for Red Hat and partners to publish content that has been tested and is supported by Red Hat.
- **AAX Implementation:** Not applicable / out of scope
- **Reason:** Requires Red Hat certification and is a commercial offering. AAX provides equivalent functionality via **Private Automation Hub** for custom and community content.
- **Alternative in AAX:** Use Private Automation Hub to:
  - Host custom Ansible Collections
  - Pull from community sources (galaxy.ansible.com)
  - Integrate with CI/CD pipelines
  - Create enterprise content repositories
- **Recommendation:** For certified Red Hat content, subscribe to Red Hat AAP and synchronize with Private Automation Hub

---

## Gap Analysis Summary

| Aspect                      | Status         | Details                                                           |
| --------------------------- | -------------- | ----------------------------------------------------------------- |
| **Core Automation**         | Complete       | AWX + execution environments cover full automation stack          |
| **Content Management**      | Complete       | Private Automation Hub covers custom and community content        |
| **Distributed Execution**   | Complete       | Receptor mesh for distributed job execution                       |
| **Content Development**     | Complete       | ansible-builder and ansible-navigator included                    |
| **Event-Driven Automation** | Complete       | ansible-rulebook EDA controller now fully integrated              |
| **High Availability**       | Partial        | Single-node Docker Compose; HA requires external LB or Kubernetes |
| **Certified Content**       | Not Applicable | Would require Red Hat subscription; use Private Hub instead       |
| **Enterprise RBAC**         | Supported      | AWX RBAC; can extend with LDAP/SAML via AWX plugins               |
| **Audit & Compliance**      | Supported      | Execution history and logging in PostgreSQL                       |

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

```bash
docker compose --profile hub up -d
# Access at http://localhost:15001
```

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

### Event-Driven Automation

```bash
docker compose --profile eda up -d
# Access at http://localhost:5000
```

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
