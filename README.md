# AAX - Ansible Automation Platform Alternative

[![CI](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml)
[![Release](https://github.com/kpeacocke/AAX/actions/workflows/release.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/release.yml)

A containerized, open-source implementation of Ansible Automation Platform (AAP) functionality using upstream components and Docker Compose.

## Overview

This project provides a production-ready Docker Compose setup that replicates core Ansible Automation Platform capabilities using open-source components. It enables organizations to run automation workflows, manage inventories, and execute playbooks in a containerized environment.

## Architecture

The platform consists of the following containerized services:

- **AWX** - Web-based UI and API for automation workflows
- **PostgreSQL** - Database backend for AWX and automation controller
- **Redis** - Message broker for task distribution
- **Receptor** - Overlay network for distributed automation execution
- **Execution Environments** - Container images for running Ansible playbooks
- **Private Automation Hub** - Galaxy NG and Pulp for hosting Ansible collections and execution environments
- **Event-Driven Ansible** - ansible-rulebook and EDA server for automated event responses (coming soon)

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later
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
   docker-compose up -d
   ```

4. **Access the web interface**

   - URL: <http://localhost:8080>
   - Default credentials will be output in the logs:

     ```bash
     docker-compose logs awx_web | grep "Admin password"
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
make build-ee-base

# Build execution environment builder
make build-ee-builder

# Build development tools
make build-dev-tools

# Build all images
make build-images
```

### Using Docker Compose for Local Development

The project includes a `docker-compose.yml` for easy local development:

```bash
# Build all images
make compose-build
# or: docker compose build

# Start all services
make compose-up
# or: docker compose up -d

# View service status
make compose-ps
# or: docker compose ps

# View logs
make compose-logs
# or: docker compose logs -f

# Stop all services
make compose-down
# or: docker compose down
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
docker-compose build

# Build specific service
docker-compose build awx_web
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
docker-compose exec postgres pg_dump -U awx awx > backup.sql

# Volume backup
docker run --rm -v aax_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .
```

### Restore

```bash
# Database restore
docker-compose exec -T postgres psql -U awx awx < backup.sql

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

# Build images
make build-images

# Run tests
make test              # Run pytest test suite
make test-all          # Build and test all images
make ci                # Full CI pipeline locally
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
make k8s-deploy
# Or: kubectl apply -k k8s/

# Check deployment status
make k8s-status
# Or: kubectl get all -n aax

# Test the deployment
make k8s-test
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
make k8s-logs

# Execute shell in a pod
make k8s-exec

# Restart all deployments
make k8s-restart

# Delete the deployment
make k8s-delete
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
make controller-up

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
make controller-status  # Show container status
make controller-logs    # View logs
make controller-down    # Stop services
make controller-clean   # Remove all data (destructive)
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
2. Rebuild images: `docker-compose build --no-cache`
3. Run migration: `docker-compose exec awx_web awx-manage migrate`
4. Test thoroughly in staging environment

## Private Automation Hub

The AAX project includes a complete Private Automation Hub implementation using Galaxy NG and Pulp for hosting Ansible collections and execution environment container images.

### Hub Quick Start

```bash
# Start the hub stack
make hub-up

# Or manually:
docker compose -f docker-compose.hub.yml up -d
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
make hub-status   # Show container status
make hub-logs     # View logs
make hub-restart  # Restart services
make hub-down     # Stop services
make hub-clean    # Remove all data (destructive)
make hub-test     # Test API endpoints
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
docker-compose logs

# Verify resources
docker stats
```

#### Database connection errors

```bash
# Ensure PostgreSQL is healthy
docker-compose exec postgres pg_isready

# Check network connectivity
docker-compose exec awx_web nc -zv postgres 5432
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

## License

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) file for details.

Individual components maintain their original licenses:

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

## Acknowledgments

Built on the shoulders of giants:

- [AWX Project](https://github.com/ansible/awx)
- [Ansible](https://github.com/ansible/ansible)
- [Receptor](https://github.com/ansible/receptor)

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Red Hat, Inc. or Ansible, Inc. All trademarks are property of their respective owners.
