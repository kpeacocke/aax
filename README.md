# AAX - Ansible Automation Platform Alternative

[![CI](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml)
[![Release](https://github.com/kpeacocke/AAX/actions/workflows/release.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/release.yml)

A containerised, open-source implementation of Ansible Automation Platform (AAP) functionality using upstream components and Docker Compose.

## Overview

This project provides a production-ready Docker Compose setup that replicates core Ansible Automation Platform capabilities using open-source components. It enables organisations to run automation workflows, manage inventories, and execute playbooks in a containerised environment.

## Why AAX?

AAX is an open-source alternative to Red Hat's commercial Ansible Automation Platform, built entirely from upstream open-source projects. Choose AAX if you:

- **Want to avoid vendor lock-in** - Full source code, no subscription required
- **Prefer transparency** - Build all components from source, see exactly what's running
- **Need cost-effective automation** - Run at scale without per-node licensing fees
- **Require self-hosted control** - Complete control over your automation infrastructure
- **Are in development/testing** - Ideal for learning, prototyping, and non-critical workloads
- **Value open-source** - Contribute and customise freely under Apache 2.0

### Project Status

**AAX is suitable for:**

- Development and testing environments
- Learning and experimentation
- Small to medium-scale deployments
- Organisations with open-source preference

**Consider Red Hat's commercial AAP if you need:**

- Enterprise support contracts
- Advanced RBAC and SSO integrations
- Certified support for production environments
- Fully managed SaaS offering

## Architecture

AAX orchestrates core Ansible Automation Platform components built entirely from upstream open-source projects.

### Automation Controller (Official AAP Component 3.2)

**AWX** - Automation controller with web UI and REST API (upstream: [ansible/awx](https://github.com/ansible/awx) v24.6.1)

- `awx-web` - Web interface and REST API
- `awx-task` - Job dispatcher and execution engine
- `awx-postgres` - PostgreSQL database backend (Official Component 3.10)
- `awx-redis` - Redis message broker and cache

### Private Automation Hub (Official AAP Component 3.3)

**Galaxy NG** - ASGI application for Ansible collection and execution environment hosting (upstream: [ansible/galaxy_ng](https://github.com/ansible/galaxy_ng) v4.9.2)
**Pulp** - Content management platform for hosting collections and container images (upstream: [pulpproject/pulp](https://github.com/pulpproject/pulp))

- `galaxy-ng` - Galaxy NG web UI and API
- `pulp-api` - Content management API
- `pulp-content` - Content delivery service  
- `pulp-worker` - Background task processor
- `hub-postgres` - PostgreSQL database backend (Official Component 3.10)
- `hub-redis` - Redis cache and message broker

### Automation Execution Environments (Official AAP Component 3.7)

Container images on which all automation in AAX is run, including Ansible execution engine and modules:

- `ee-base` - Base execution environment with Ansible Core 2.20.0
- `ee-builder` - EE builder with ansible-builder (upstream: [ansible/ansible-builder](https://github.com/ansible/ansible-builder) v3.1.0)
- `dev-tools` - Development tools for content creation and testing (includes components 3.8 & 3.9)

### Automation Content Navigator (Official AAP Component 3.9)

Textual user interface (TUI) for content building and running automation locally:

- Included in `dev-tools` image (upstream: [ansible/ansible-navigator](https://github.com/ansible/ansible-navigator) v24.2.0)
- ansible-lint (upstream: [ansible/ansible-lint](https://github.com/ansible/ansible-lint) v25.12.1)

### Automation Mesh (Official AAP Component 3.6)

**Receptor** - Overlay network for distributed execution and work distribution (upstream: [ansible/receptor](https://github.com/ansible/receptor))

- Enables peer-to-peer mesh communication
- Supports distributed job execution
- Used for automation controller → execution node communication

### Event-Driven Ansible Controller (Official AAP Component 3.5) - ✅ Now Implemented

**ansible-rulebook** - Event-driven automation engine for automated IT request resolution (upstream: [ansible/ansible-rulebook](https://github.com/ansible/ansible-rulebook) v1.1.3)

- Enables event-driven automation with rulebooks
- Integrates with event sources (webhooks, monitoring, APIs)
- Triggers Automation Controller actions on events
- Real-time event processing and automation
- Scalable event distribution via Redis
- PostgreSQL storage for rulebook definitions and event history
- REST API for rulebook management (port 5000)
- WebSocket support for real-time event streaming

**Deploy EDA:**

```bash
docker compose -f docker-compose.eda.yml --profile eda up -d
curl http://localhost:5000/health
```

**Documentation:** See [images/eda-controller/README.md](images/eda-controller/README.md) for detailed EDA usage, rulebook examples, and integration patterns.

## Red Hat AAP 2.6 Components Coverage

AAX implements core Ansible Automation Platform components from the official Red Hat documentation. Below is the comprehensive mapping of all official AAP components (Red Hat AAP 2.6) to their AAX implementation status.

**📋 For detailed component information, see [COMPONENTS.md](COMPONENTS.md) - Complete mapping of all 10 official AAP components, design decisions, and gap analysis.**

| Component                             | Official Description                                                               | AAX Status               | Upstream Project                                                                                                      | Notes                                                                                                               |
| ------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Ansible automation hub**            | Repository for Red Hat certified Ansible Content Collections                       | ❌ Not Implemented        | N/A                                                                                                                   | Requires Red Hat certification; AAX uses Private Automation Hub instead for custom collections                      |
| **Automation controller**             | Enterprise framework for defining, operating, and scaling Ansible automation       | ✅ Implemented            | [ansible/awx](https://github.com/ansible/awx) (v24.6.1)                                                               | Full AWX stack with web UI, API, postgres, redis                                                                    |
| **Private automation hub**            | On-premise solution for synchronizing and serving custom collections and EE images | ✅ Implemented            | [ansible/galaxy_ng](https://github.com/ansible/galaxy_ng) + [pulp/pulp_ansible](https://github.com/pulp/pulp_ansible) | Supports custom collections, EE image registry, CI/CD integration                                                   |
| **High availability automation hub**  | Multi-node active-active configuration with load balancer                          | ⚠️ Partial                | N/A                                                                                                                   | Single-node Docker Compose; HA requires external load balancer (see [docs/HA-DEPLOYMENT.md](docs/HA-DEPLOYMENT.md)) |
| **Event-Driven Ansible controller**   | Interface for event-driven automation using rulebooks                              | ✅ Implemented            | [ansible/ansible-rulebook](https://github.com/ansible/ansible-rulebook) (v1.1.3)                                      | Full EDA controller with REST API, rulebook execution, webhook support                                              |
| **Automation mesh**                   | Overlay network for distributed work distribution and execution                    | ✅ Implemented            | [ansible/receptor](https://github.com/ansible/receptor)                                                               | Full Receptor mesh networking for execution distribution                                                            |
| **Automation execution environments** | Container images for running all automation in AAP                                 | ✅ Implemented            | [ansible/ansible-builder](https://github.com/ansible/ansible-builder)                                                 | ee-base (Ansible 2.20.0), ee-builder, dev-tools images                                                              |
| **Ansible Galaxy**                    | Hub for finding and reusing Ansible content                                        | ✅ Used as Content Source | [ansible/galaxy](https://github.com/ansible/galaxy)                                                                   | Private hub can pull from galaxy.ansible.com and other registries                                                   |
| **Automation content navigator**      | TUI for content building and running automation                                    | ✅ Implemented            | [ansible/ansible-navigator](https://github.com/ansible/ansible-navigator) (v24.2.0)                                   | Included in dev-tools image; covers content building and local EE execution                                         |
| **PostgreSQL**                        | Backend relational database for storing automation data                            | ✅ Implemented            | PostgreSQL 15                                                                                                         | Multiple instances: awx-postgres, hub-postgres, eda-postgres                                                        |

### Component Implementation Summary

- **Fully Implemented (8):** Automation controller, Private automation hub, Automation mesh, Automation execution environments, Event-Driven Ansible controller, Ansible Galaxy (as source), Automation content navigator, PostgreSQL
- **Partially Implemented (1):** High availability automation hub (single-node DC; full HA requires external load balancer, see [docs/HA-DEPLOYMENT.md](docs/HA-DEPLOYMENT.md))
- **Not Applicable (1):** Ansible automation hub (Red Hat certified content; use Private Automation Hub for custom content)

### AAX vs. Red Hat Ansible Automation Platform

| Feature              | Red Hat AAP                  | AAX                          |
| -------------------- | ---------------------------- | ---------------------------- |
| **Source**           | Proprietary                  | 100% open-source upstream    |
| **Cost**             | Subscription (per-node)      | Free (Apache 2.0)            |
| **Build**            | Pre-built images             | Built from source            |
| **Support**          | Enterprise support available | Community support            |
| **Deployment**       | Cloud/on-prem                | Docker Compose, Kubernetes   |
| **RBAC & Auth**      | Advanced (LDAP/SAML/OAuth)   | Basic (extendable)           |
| **Production Ready** | Yes, enterprise grade        | Yes, for self-supported use  |
| **Vendor Lock-in**   | High                         | None                         |
| **Customisation**    | Limited                      | Full source access           |
| **AAP Components**   | All 10 components            | 9/10 components (HA partial) |

**Disclaimer:** AAX is not affiliated with, endorsed by, or sponsored by Red Hat, Inc. or Ansible, Inc.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 5.1.0 or later
- Minimum 4GB RAM allocated to Docker
- 20GB available disk space
- Supported platforms: macOS, Windows (WSL2), Linux

## Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/kpeacocke/AAX.git
   cd AAX
   ```

2. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

3. **Start the services**

  ```bash
  docker compose --profile controller up -d
  ```

1. **Access the web interface**

   - URL: <http://localhost:8080>
   - Default credentials will be output in the logs:

    ```bash
    docker compose --profile controller logs awx-web | grep "Admin password"
    ```

## Configuration

### Environment Variables

Key environment variables in `.env`:

- `AAX_ADMIN_PASSWORD` - Initial admin password (change immediately)
- `POSTGRES_PASSWORD` - Database password
- `SECRET_KEY` - Django secret key for AWX
- `RECEPTOR_PEERS` - Comma-separated list of receptor mesh nodes

### Volumes

Persistent data is stored in Docker volumes:

- `postgres_data` - Database storage
- `receptor_data` - Receptor mesh state
- `awx_projects` - Git repositories and project files
- `awx_redis` - Redis cache data

### Custom Execution Environments

To add custom execution environments:

1. Build your execution environment image
2. Add the image to `docker-compose.yml`
3. Register it in AWX through the UI or API

## Building from Source

### Execution Environment Images

Build custom Ansible Execution Environment images:

```bash
# Build base execution environment
docker build -f images/ee-base/Dockerfile -t aax/ee-base:latest images/ee-base/

# Build execution environment builder
docker build -f images/ee-builder/Dockerfile -t aax/ee-builder:latest images/ee-builder/

# Build development tools
docker build -f images/dev-tools/Dockerfile -t aax/dev-tools:latest images/dev-tools/

# Build all images including hub
docker build -f images/pulp/Dockerfile.pulp -t aax/pulp:latest images/pulp/
docker build -f images/galaxy-ng/Dockerfile -t aax/galaxy-ng:latest images/galaxy-ng/
docker build -f images/awx/Dockerfile -t aax/awx:latest images/awx/
docker build -f images/receptor/Dockerfile -t aax/receptor:latest images/receptor/
```

### Using Docker Compose for Local Development

The project includes a core `docker-compose.yml` that can include the controller and hub stacks while keeping them modular via profiles:

```bash
# Build core images
docker compose build

# Build all images (core + controller + hub)
docker compose --profile controller --profile hub build

# Start core services only (default)
docker compose up -d

# Start core + controller stack
docker compose --profile controller up -d

# Start core + hub stack
docker compose --profile hub up -d

# Start everything
docker compose --profile controller --profile hub up -d

# View service status
docker compose ps

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

Services include:

- `ee-base` - Base execution environment with ansible-core 2.20.0
- `ee-builder` - Execution environment builder with ansible-builder 3.1.0
- `dev-tools` - Development tools with ansible-navigator, ansible-lint, and ansible-dev-tools

### Using ansible-builder for Custom EEs

Create an `execution-environment.yml`:

```yaml
version: 3
images:
  base_image:
    name: aax/ee-base:latest
dependencies:
  galaxy: requirements.yml
  python: requirements.txt
  system: bindep.txt
```

Build your custom execution environment:

```bash
# Using the dev-tools container
docker compose run --rm dev-tools ansible-builder build --tag my-custom-ee:latest

# Or using the ee-builder container directly
docker run --rm -it \
  -v $(pwd):/workspace \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aax/ee-builder:latest \
  ansible-builder build --tag my-custom-ee:latest
```

### Platform Components

All platform components are built from upstream open-source repositories:

```bash
# Build all services
docker compose --profile controller --profile hub build

# Build specific service
docker compose --profile controller build awx-web
```

See `docker-compose.build.yml` for build configurations.

## Production Deployment

### Security Hardening

1. **Change default passwords** immediately after first deployment
2. **Enable HTTPS** using a reverse proxy (nginx, Traefik, Caddy)
3. **Restrict network access** using firewall rules
4. **Enable authentication** (LDAP, SAML, OAuth)
5. **Regular updates** of all container images

### High Availability

For production HA deployments:

1. Deploy multiple AWX instances with a load balancer
2. Use external PostgreSQL cluster with replication
3. Deploy Redis Sentinel for cache HA
4. Configure receptor mesh across multiple availability zones

### Monitoring

Integrate with:

- Prometheus for metrics collection
- Grafana for visualization
- ELK/Loki for log aggregation
- Health check endpoints at `/api/v2/ping`

## Backup and Restore

### Backup

```bash
# Database backup
docker compose --profile controller exec postgres pg_dump -U awx awx > backup.sql

# Volume backup
docker run --rm -v aax_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .
```

### Restore

```bash
# Database restore
docker compose --profile controller exec -T postgres psql -U awx awx < backup.sql

# Volume restore
docker run --rm -v aax_postgres_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_data.tar.gz -C /data
```

## Development

### Local Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt
pip install pytest

# Run linters
pre-commit run --all-files

# Build and test images
docker compose build

# Run tests
pytest tests/ -v              # Run pytest test suite
pytest tests/test_images.py  # Test container images
pytest tests/test_compose.py # Test docker compose
```

### Testing

The project includes comprehensive automated tests:

- **Unit tests** - Python pytest suite in `tests/`
- **Integration tests** - Docker image build and functionality tests
- **Linting** - Hadolint for Dockerfiles, pre-commit hooks
- **Security scanning** - Trivy vulnerability scanning

#### Running Tests in VS Code

Tests are integrated with VS Code Test Explorer:

1. Open Testing view (`Cmd+Shift+T`)
2. Tests auto-discover from `tests/` directory
3. Click ▶️ to run individual or all tests
4. View results inline with pass/fail indicators

See [tests/README.md](tests/README.md) for detailed testing documentation.

### CI/CD Pipelines

The project uses GitHub Actions for automated testing and releases:

- **CI Pipeline** ([ci.yml](.github/workflows/ci.yml))
  - Runs on all branches and pull requests
  - Lints code and Dockerfiles
  - Builds and tests all images
  - Security scanning on develop branch

- **Release Pipeline** ([release.yml](.github/workflows/release.yml))
  - Runs on merges to main
  - Full test suite (blocking)
  - Security scan (blocking)
  - Semantic versioning with release-please
  - Pushes images to GitHub Container Registry

For detailed workflow documentation, see [.github/workflows/README.md](.github/workflows/README.md).

## Kubernetes Deployment

The AAX platform can also be deployed to Kubernetes using the provided manifests in the `k8s/` directory.

### Kubernetes Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl CLI configured
- Container images built and available
- Storage class available (default: `hostpath` for Docker Desktop)

### Kubernetes Quick Start

Deploy to Kubernetes:

```bash
# Deploy all resources
kubectl apply -k k8s/

# Check deployment status
kubectl get all -n aax

# Test the deployment
pytest tests/test_kubernetes.py -v
```

> **Note**: The Kubernetes test suite (`tests/test_kubernetes.py`) requires a configured Kubernetes cluster. `kubectl` is installed in the dev container, but you need to enable Kubernetes in Docker Desktop or configure another cluster for the tests to run.

### Kubernetes Resources

The deployment creates:

- **Namespace**: `aax` - Isolated namespace for all resources
- **Deployments**: ee-base, ee-builder, dev-tools (1 replica each)
- **Services**: ClusterIP services for inter-pod communication
- **PersistentVolumeClaims**: workspace, ee-builds, ee-definitions, dev-workspace
- **ConfigMap**: Shared environment configuration

### Managing the Deployment

```bash
# View pod logs
kubectl logs -n aax -f deployment/ee-base

# Execute shell in a pod
kubectl exec -n aax -it deployment/ee-base -- /bin/bash

# Restart all deployments
kubectl rollout restart -n aax deployment/ee-base
kubectl rollout restart -n aax deployment/ee-builder
kubectl rollout restart -n aax deployment/dev-tools

# Delete the deployment
kubectl delete -k k8s/
```

### Accessing Services

```bash
# Execute commands in pods
kubectl exec -n aax deployment/ee-base -- ansible --version
kubectl exec -n aax deployment/ee-builder -- ansible-builder --version
kubectl exec -n aax deployment/dev-tools -- ansible-navigator --version
kubectl exec -n aax deployment/dev-tools -- ansible-lint --version

# Get an interactive shell
kubectl exec -it -n aax deployment/dev-tools -- /bin/bash
```

### Resource Configuration

Each deployment has:

- **CPU**: 1-2 cores (1 requested, 2 limit)
- **Memory**: 1-2Gi (1Gi requested, 2Gi limit)
- **Health Checks**: Liveness and readiness probes
- **Security**: Non-root user, dropped capabilities

### Storage

Persistent volumes for:

- `workspace` (10Gi) - Shared workspace for Ansible operations
- `ee-builds` (20Gi) - Execution environment build outputs
- `ee-definitions` (5Gi) - EE definition files
- `dev-workspace` (10Gi) - Development workspace

### Production Considerations

For production deployments:

1. **Update storage class** in `k8s/persistent-volumes.yaml` to use cloud provider storage
2. **Change access mode** from `ReadWriteOnce` to `ReadWriteMany` if using NFS/CephFS
3. **Increase replicas** for high availability
4. **Configure ingress** for external access
5. **Set up monitoring** with Prometheus/Grafana
6. **Implement backup** for persistent volumes

See [k8s/README.md](k8s/README.md) for detailed Kubernetes deployment documentation.

## AWX Controller Stack

The AAX project includes a complete AWX (Ansible Automation Platform controller) deployment with Receptor mesh networking.

### Controller Quick Start

```bash
# Start the controller stack (includes PostgreSQL, Redis, AWX, and Receptor)
docker compose --profile controller up -d

# Access AWX at http://localhost:8080
# Username: admin
# Password: password
```

### Features

- **AWX 24.6.1** - Full automation controller with web UI and API
- **Receptor Mesh** - Distributed execution network
- **Pre-configured** - Uses `aax/ee-base:latest` as default execution environment
- **PostgreSQL** - Persistent database backend
- **Redis** - Message broker and cache

### Management Commands

```bash
docker compose --profile controller ps          # Show container status
docker compose --profile controller logs -f     # View logs
docker compose --profile controller down        # Stop services
docker compose --profile controller down -v     # Remove all data (destructive)
```

See [controller/README.md](controller/README.md) for detailed controller documentation including:

- Running your first job
- API access examples  
- Receptor mesh configuration
- Backup and restore procedures
- Production deployment considerations

### Updating Components

To update to latest upstream versions:

1. Update version tags in `docker-compose.yml`
2. Rebuild images: `docker compose build --no-cache`
3. Run migration: `docker compose exec awx-web awx-manage migrate`
4. Test thoroughly in staging environment

## Private Automation Hub

The AAX project includes a complete Private Automation Hub implementation using Galaxy NG and Pulp for hosting Ansible collections and execution environment container images.

### Hub Quick Start

```bash
# Start the hub stack
docker compose --profile hub up -d
```

**Access the Hub:**

- Galaxy NG UI: <http://localhost:5001>
- Pulp API: <http://localhost:24817/pulp/api/v3/>
- Content Delivery: <http://localhost:24816>

Default credentials: `admin` / `changeme`

### Hub Features

1. **Collection Management** - Host and distribute private Ansible collections
2. **Content Approval Workflow** - Review and approve collections before publishing
3. **Execution Environment Registry** - Store custom EE container images
4. **Content Signing** - GPG signing for collections and containers
5. **RBAC** - Role-based access control for content management
6. **API Access** - Full REST API for automation

### Publishing Collections

#### Using ansible-galaxy CLI

```bash
# Configure ansible-galaxy
cat >> ~/.ansible.cfg << EOF
[galaxy]
server_list = private_hub

[galaxy_server.private_hub]
url=http://localhost:5001/api/galaxy/
token=<your-api-token>
EOF

# Build and publish
ansible-galaxy collection build
ansible-galaxy collection publish namespace-collection-1.0.0.tar.gz
```

#### Using the UI

1. Navigate to <http://localhost:5001>
2. Log in with admin credentials
3. Go to "Collections" → "Upload Collection"
4. Upload your `.tar.gz` file

### Integration with AWX

Configure AWX to use your private hub:

1. In AWX UI, create Galaxy/Hub API Token credential
2. Set Galaxy Server URL: `http://galaxy-ng:5001/api/galaxy/`
3. Add token from Hub UI
4. Use credential in projects with `requirements.yml`

### Hub Management Commands

```bash
docker compose --profile hub ps         # Show container status
docker compose --profile hub logs -f    # View logs
docker compose --profile hub restart    # Restart services
docker compose --profile hub down       # Stop services
docker compose --profile hub down -v    # Remove all data (destructive)
```

See [hub/README.md](hub/README.md) for detailed hub documentation including:

- Content approval workflows
- Collection signing setup
- Container registry usage
- API examples
- Backup and restore procedures
- Production deployment considerations

## Troubleshooting

### Common Issues

#### Services fail to start

```bash
# Check logs
docker compose logs

# Verify resources
docker stats
```

#### Database connection errors

```bash
# Ensure PostgreSQL is healthy
docker compose --profile controller exec postgres pg_isready

# Check network connectivity
docker compose --profile controller exec awx-web nc -zv postgres 5432
```

#### Permission issues on Windows/WSL2

```bash
# Ensure proper line endings
git config core.autocrlf input
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code of conduct
- Development workflow
- Pull request process
- Coding standards

## Licence

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) file for details.

Individual components maintain their original licences:

- AWX: Apache 2.0
- Ansible: GPL 3.0
- PostgreSQL: PostgreSQL License
- Redis: BSD-3-Clause

## Security

For security issues, please see our [Security Policy](SECURITY.md).

## Support

- **Issues**: [GitHub Issues](https://github.com/kpeacocke/AAX/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kpeacocke/AAX/discussions)
- **Documentation**: [Wiki](https://github.com/kpeacocke/AAX/wiki)

## Acknowledgements

Built on the shoulders of giants:

- [AWX Project](https://github.com/ansible/awx)
- [Ansible](https://github.com/ansible/ansible)
- [Receptor](https://github.com/ansible/receptor)

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Red Hat, Inc. or Ansible, Inc. All trademarks are property of their respective owners.
