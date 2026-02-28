# AAX Architecture

AAX is built from upstream Ansible and Red Hat projects, orchestrated with Docker Compose for easy deployment and development.

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         AAX Stack                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         User Interface & API Gateways (Port 8080)        │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  AWX Web UI │ Galaxy NG UI │ Pulp API │ EDA Controller   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │     Core Services (Control Plane)                        │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │   │
│  │  │ AWX Controller  │  │ Galaxy NG + Pulp             │   │   │
│  │  │ - Web Service   │  │ - Private Automation Hub     │   │   │
│  │  │ - Task Engine   │  │ - Content Management         │   │   │
│  │  │ - API           │  │ - Repository                 │   │   │
│  │  └─────────────────┘  └──────────────────────────────┘   │   │
│  │                                                          │   │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │   │
│  │  │ EDA Controller  │  │ Development Tools            │   │   │
│  │  │ - Event Engine  │  │ - ansible-navigator          │   │   │
│  │  │ - Rulebook      │  │ - ansible-lint               │   │   │
│  │  │ - Webhooks      │  │ - Dev Utilities              │   │   │
│  │  └─────────────────┘  └──────────────────────────────┘   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │     Data & Cache Layer                                   │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  PostgreSQL      │    Redis         │    Volumes         │   │
│  │  - 5 Databases   │    - Cache       │    - Storage       │   │
│  │  - Persistence   │    - Job Queue   │    - Credentials   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │     Execution Environments                               │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  ee-base (Execution)  │  ee-builder (Build)              │   │
│  │  - Ansible Core       │  - ansible-builder               │   │
│  │  - Base Python Tools  │  - Builds custom EE images       │   │
│  │  - SSH, Git, RSA...   │  - Python, Ansible packages      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│         Automation Mesh (Receptor Network)                      │
├─────────────────────────────────────────────────────────────────┤
│  Enables distributed automation across nodes and networks       │
└─────────────────────────────────────────────────────────────────┘
```

## Component Stack

### Core Automation Controller

**AWX** – Open source automation controller from Red Hat

- **Web Service**: REST API and web UI  (port 8052)
- **Task Engine**: Celery-based job execution
- **Database**: PostgreSQL for persistence
- **Cache**: Redis for session and job queue
- **Features**:
  - Job templates and scheduling
  - Inventory management
  - Credential storage (encrypted)
  - RBAC and multi-tenancy
  - Webhooks and event notifications
  - Receptor integration for distributed execution

### Private Automation Hub

**Galaxy NG** & **Pulp** – Content repository and distribution

- **Galaxy NG** (port 8000): Web UI and API for content discovery
- **Pulp** (port 24816-24817): Content management backend
- **Features**:
  - Ansible collection repository
  - Role distribution
  - Container image storage
  - Access control and signing
  - Namespace management
  - Multi-repository support

### Event-Driven Automation

**EDA Controller** – Event-driven automation engine

- **Rulebook Engine**: Processes event-triggered rules
- **Webhook Server**: Receives events from external systems
- **Action Execution**: Triggers Ansible playbooks or webhooks
- **Features**:
  - Event source integrations
  - Conditional rule processing
  - Action templating
  - Multi-tenant support
  - History and audit logging

### Execution Environments

**ee-base**, **ee-builder**, **dev-tools** – Containerized execution

- **ee-base**: Base execution environment
  - Ansible Core
  - Python runtime
  - Collection dependencies
  - SSH, Git, networking tools

- **ee-builder**: Builds custom execution environments
  - ansible-builder
  - Build utilities
  - Creates optimized images for specific needs

- **dev-tools**: Development and testing tools
  - ansible-navigator: EE exploration
  - ansible-lint: Playbook linting
  - Development utilities

### Automation Mesh

**Receptor** – Distributed automation network

- Enables controller-to-controller communication
- Node clustering without a central broker
- Mesh resilience and redundancy
- Hot-standby capabilities
- Multi-hop routing

### Data Persistence

**PostgreSQL** + **Redis** + **Docker Volumes**

- **PostgreSQL**: Primary datastore
  - AWX database (automation state)
  - Galaxy/Pulp database (content metadata)
  - EDA database (rule definitions)
  - User credentials and configuration

- **Redis**: High-speed cache and messaging
  - Session cache
  - Task queue
  - Celery job broker
  - Real-time data

- **Docker Volumes**: File storage
  - SSH keys and credentials
  - Project playbooks
  - Artifact uploads
  - Log files

## Communication Patterns

### Service-to-Service

``` text
AWX Web Service
    ↓
AWX Task Worker (Celery)
    ↓
Execution Environment (ee-base)
    ↓
Ansible Playbook Execution
    ↓
Managed Nodes
```

### API Communication

``` text
Client (curl, UI, SDK)
    ↓ HTTP/REST
AWX API Gateway (port 8080)
    ↓
AWX Web Service (port 8052)
    ↓ SQL/Redis
PostgreSQL + Redis
```

### Event Flow

``` text
External Event Source
    ↓ Webhook
EDA Controller (port 5000)
    ↓ Check Rules
Process Rulebook
    ↓ If Matched
Execute Action
    ↓
Trigger Playbook in AWX
    ↓
Execution Environment
    ↓
Managed Node
```

### Content Distribution

``` text
User/Developer
    ↓ Upload
Galaxy NG Web UI (port 8000)
    ↓ Store
Pulp Backend (port 24816)
    ↓
PostgreSQL (metadata)
    ↓
Docker Volume (artifacts)
    ↓
Consumer pulls via Galaxy API
```

## Network Topology

### Local Development (Docker Compose)

```text
┌─────────────────────────────┐
│   Host Machine              │
│  (Docker Engine)            │
├─────────────────────────────┤
│  docker0 Network            │
│  172.17.0.0/16              │
│                             │
│  ┌──────────────────────┐  │
│  │ awx-web (172.17...)  │  │
│  │ :8080 → :8052        │  │
│  └──────────────────────┘  │
│           ↓                 │
│  ┌──────────────────────┐  │
│  │ postgres (172.17..)  │  │
│  │ :5432                │  │
│  └──────────────────────┘  │
│           ↓                 │
│  ┌──────────────────────┐  │
│  │ redis (172.17...)    │  │
│  │ :6379                │  │
│  └──────────────────────┘  │
│                             │
│  volumes/                   │
│  ├── awx-data               │
│  ├── postgres-data          │
│  └── redis-data             │
└─────────────────────────────┘
```

### Kubernetes Deployment

``` text
┌──────────────────────────────────┐
│      Kubernetes Cluster          │
├──────────────────────────────────┤
│  namespace: aax                  │
│                                  │
│  Deployment: awx-web             │
│  ├─ Container: awx-web           │
│  ├─ Service: awx-web (8080)      │
│  └─ ConfigMap, Secrets           │
│                                  │
│  Deployment: awx-task            │
│  └─ Container: awx-task          │
│                                  │
│  StatefulSet: postgres           │
│  ├─ Container: postgres          │
│  ├─ Service: postgres (5432)     │
│  └─ PersistentVolumeClaim        │
│                                  │
│  Deployment: galaxy-ng           │
│  └─ Service: galaxy-ng (8000)    │
│                                  │
│  Deployment: eda-controller      │
│  └─ Service: eda-controller      │
│                                  │
│  ConfigMap: tower-settings       │
│  Secret: db-credentials          │
└──────────────────────────────────┘
```

## Data Flow

### Job Execution Flow

``` text
1. User creates Job Template in AWX UI
                ↓
2. User launches job via Web UI or API
                ↓
3. AWX Web Service queues job to Redis
                ↓
4. Celery Task Worker picks up job
                ↓
5. Task Server pulls Job playbook from project volume
                ↓
6. Executor spawns Execution Environment container (ee-base)
                ↓
7. Ansible runs playbook in EE against managed nodes
                ↓
8. Results streamed back to AWX Web Service
                ↓
9. Job output stored in PostgreSQL
                ↓
10. User views results in AWX UI
```

### Content Publishing Flow

``` text
1. Developer creates/updates Ansible collection
                ↓
2. Run: ansible-galaxy publish
                ↓
3. Galaxy NG API receives collection (port 8080)
                ↓
4. Pulp validates and processes collection
                ↓
5. Metadata stored in PostgreSQL
                ↓
6. Collection artifacts stored in docker volume
                ↓
7. Galaxy NG indexes in search
                ↓
8. Consumers can download via Galaxy API/CLI
```

### Event Processing Flow

``` text
1. External event source (webhook, message queue, etc.)
                ↓
2. Sends HTTP POST to EDA Webhook endpoint (port 5000)
                ↓
3. EDA receives and queues event
                ↓
4. EDA Rulebook Engine processes event
                ↓
5. Evaluates event against rules in PostgreSQL
                ↓
6. If matched, executes action (trigger AWX job, webhook, etc.)
                ↓
7. Action execution tracked in EDA database
```

## Scaling Considerations

### Horizontal Scaling

- **AWX Web**: Multiple instances behind load balancer
- **AWX Task**: Horizontal scaling for job throughput
- **Celery Workers**: Additional workers in Receptor nodes
- **PostgreSQL**: Replication for read-heavy workloads
- **Redis**: Sentinel or Cluster mode for HA

### Resource Requirements

``` text
Minimal Setup:
├─ 4 GB RAM
├─ 20 GB Disk
└─ 2 CPU cores

Recommended:
├─ 8 GB RAM
├─ 50 GB Disk
└─ 4 CPU cores

Production (HA):
├─ 16+ GB RAM
├─ 100+ GB Disk
├─ 8+ CPU cores
└─ Multiple nodes
```

## Security Architecture

### Service Isolation

- Containers run as non-root users
- Network policies restrict inter-container communication
- Docker secrets for sensitive data
- Volume permissions enforced

### Data Protection

- PostgreSQL connections use TLS
- Redis optionally secured
- Encrypted credentials in database
- Log sanitization (removes secrets)
- RBAC enforced at API level

### Authentication & Authorization

- Local user database
- LDAP/ActiveDirectory integration
- OAuth2 support
- SAML support
- Token-based API authentication

## High Availability (HA)

For production deployments, AAX supports:

### Database HA

- PostgreSQL replication (primary + standbys)
- Automated failover with Patroni
- Backup and point-in-time recovery

### Service HA

- Multiple AWX Web instances behind load balancer
- Multiple task workers for job distribution
- Receptor nodes for distributed execution
- Health checks and auto-restart

### See HA-DEPLOYMENT.md for detailed HA setup

## Component Versions

| Component  | Version | Source                     |
| ---------- | ------- | -------------------------- |
| AWX        | 24.6.1  | ansible/awx                |
| Galaxy NG  | 4.9.2   | ansible/galaxy_ng          |
| Pulp       | 3.28.43 | pulp/pulpcore              |
| EDA        | 1.1.3   | ansible/eda-server         |
| Python     | 3.11    | python (slim-bookworm)     |
| PostgreSQL | 15      | postgres (docker-official) |
| Redis      | 7       | redis (docker-official)    |

## Dependencies & Licenses

- **AWX**: Apache 2.0 - <https://github.com/ansible/awx>
- **Galaxy NG**: Apache 2.0 - <https://github.com/ansible/galaxy_ng>
- **Pulp**: GPLv2 - <https://github.com/pulp/pulpcore>
- **EDA Server**: Apache 2.0 - <https://github.com/ansible/eda-server>
- **Receptor**: Apache 2.0 - <https://github.com/ansible/receptor>
- **Ansible**: GPLv3 - <https://github.com/ansible/ansible>

## See Also

- [COMPONENTS.md](../COMPONENTS.md) – Detailed component mapping
- [README.md](../README.md) – Quick start and overview
- [HA-DEPLOYMENT.md](HA-DEPLOYMENT.md) – High availability setup
- [k8s/](../k8s/) – Kubernetes deployment manifests
- [docker-compose.yml](../docker-compose.yml) – Full service definitions
