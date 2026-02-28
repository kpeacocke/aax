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
- **Deployment:** Docker Compose (`docker-compose.controller.yml`)
- **Access:** `http://localhost:8080`

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
- **Deployment:** Docker Compose (`docker-compose.hub.yml`)
- **Access:** `http://localhost:8081`
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
- **Deployment:** Docker Compose (`docker-compose.eda.yml`) with `--profile eda`
- **Access:** REST API on `http://localhost:5000`
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

| Aspect                      | Status           | Details                                                           |
| --------------------------- | ---------------- | ----------------------------------------------------------------- |
| **Core Automation**         | ✅ Complete       | AWX + execution environments cover full automation stack          |
| **Content Management**      | ✅ Complete       | Private Automation Hub covers custom and community content        |
| **Distributed Execution**   | ✅ Complete       | Receptor mesh for distributed job execution                       |
| **Content Development**     | ✅ Complete       | ansible-builder and ansible-navigator included                    |
| **Event-Driven Automation** | ✅ Complete       | ansible-rulebook EDA controller now fully integrated              |
| **High Availability**       | ⚠️ Partial        | Single-node Docker Compose; HA requires external LB or Kubernetes |
| **Certified Content**       | ❌ Not Applicable | Would require Red Hat subscription; use Private Hub instead       |
| **Enterprise RBAC**         | ✅ Supported      | AWX RBAC; can extend with LDAP/SAML via AWX plugins               |
| **Audit & Compliance**      | ✅ Supported      | Execution history and logging in PostgreSQL                       |

## Design Decisions

### Why Not Use Pre-built Images?

AAX builds all components from source to:

- Ensure transparency and auditability
- Enable customization
- Avoid external registry dependencies
- Maintain consistency with AAX philosophy

### Why Private Hub Instead of Automation Hub?

- **Private Automation Hub** is upstream open-source equivalent of Red Hat's commercial "Automation Hub"
- Red Hat Automation Hub requires certification and subscription
- Private Automation Hub allows hosting custom content and pulling from community sources
- No licensing restrictions

### Why Event-Driven Ansible is Planned?

- Requires significant additional infrastructure (event sources, rulebook engine)
- Better implemented after core platform stabilization
- Lower priority than core automation controller and hub

### Why No Separate Automation Gateway?

- Automation Gateway is a commercial enhancement for complex multi-tenant scenarios
- Not critical for typical AAX deployments
- Can be implemented via reverse proxy (nginx/HAProxy) if needed

---

## Getting Started with Each Component

### Automation Controller

```bash
docker compose --profile controller up -d
# Access at http://localhost:8080
```

### Private Automation Hub

```bash
docker compose --profile hub up -d
# Access at http://localhost:8081
```

### Execution Environments

```bash
docker compose up -d dev-tools
docker compose exec dev-tools ansible-navigator
```

### Event-Driven Automation (Coming Soon)

```bash
# Not yet available
# Track progress: https://github.com/kpeacocke/AAX/issues
```

---

## References

- [Red Hat Ansible Automation Platform 2.6 Overview](https://docs.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.6/html/overview/index)
- [AWX Documentation](https://docs.ansible.com/awx/)
- [Pulp Project](https://pulpproject.org/)
- [Ansible Galaxy Documentation](https://docs.ansible.com/ansible/latest/galaxy/index.html)
- [Receptor Documentation](https://receptor.readthedocs.io/)
- [Ansible Navigator Documentation](https://ansible.readthedocs.io/projects/navigator/)
- [ansible-rulebook Documentation](https://docs.ansible.com/automation-rules/)

---

**Last Updated:** February 27, 2026  
**AAX Version:** 1.0.0  
**AAP Version Reference:** Red Hat AAP 2.6
