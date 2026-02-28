# AAX – Ansible Automation Platform Alternative

[![CI](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml)
[![Release](https://github.com/kpeacocke/AAX/actions/workflows/release.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/release.yml)

> **Note:** This project is maintained independently. While the author current works at Red Hat, AAX is not an official Red Hat project, product, or service. For production use, Red Hat recommends their commercial [Ansible Automation Platform](https://www.ansible.com/products/automation-platform). And so does the author.

A containerised, open-source alternative to Red Hat Ansible Automation Platform, built from upstream projects and run with Docker Compose.

## Why AAX

- Full control over your automation stack
- Built from upstream components you can inspect and customise
- Great for development, testing, learning, and self-supported production
- Gateway to AAP. Which is where you should be. *Cough*

## What You Get

AAX delivers the core AAP building blocks using upstream projects:

- **Automation controller:** AWX
- **Private automation hub:** Galaxy NG + Pulp
- **Execution environments:** ee-base, ee-builder, dev-tools
- **Event-driven automation:** ansible-rulebook
- **Automation mesh:** Receptor

For the full component mapping and status, see [COMPONENTS.md](COMPONENTS.md).

## Quick Start

```bash
git clone https://github.com/kpeacocke/AAX.git
cd AAX
cp .env.example .env

docker compose --profile controller up -d
```

- **AWX UI:** <http://localhost:8080>
- **Admin password:**

  ```bash
  docker compose --profile controller logs awx-web | grep "Admin password"
  ```

To run the hub stack:

```bash
docker compose --profile hub up -d
```

## Common Commands

```bash
# Build images
docker compose --profile controller --profile hub build

# View status
docker compose ps

# Tail logs
docker compose logs -f

# Stop everything
docker compose down
```

## Requirements

- Docker Engine 20.10+
- Docker Compose 5.1.0+
- 4 GB RAM and 20 GB disk space
- macOS, Windows (WSL2), or Linux

## Docs and Advanced Topics

- Architecture overview: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Docs index: [docs/INDEX.md](docs/INDEX.md)
- Controller stack details: [controller/CONTROLLER.md](controller/CONTROLLER.md)
- Private hub details: [hub/HUB.md](hub/HUB.md)
- EDA controller: [images/eda-controller/EDA.md](images/eda-controller/EDA.md)
- Kubernetes deployment: [k8s/K8S.md](k8s/K8S.md)
- HA guidance: [docs/HA-DEPLOYMENT.md](docs/HA-DEPLOYMENT.md)
- Testing: [tests/TESTS.md](tests/TESTS.md)

## Security

For security issues, see [SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

This project is licenced under the Apache License 2.0 – see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history and version information.

## Support

- Issues: <https://github.com/kpeacocke/AAX/issues>
- Discussions: <https://github.com/kpeacocke/AAX/discussions>
- Wiki: <https://github.com/kpeacocke/AAX/wiki>

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Red Hat, Inc. or Ansible, Inc. All trademarks are property of their respective owners.
