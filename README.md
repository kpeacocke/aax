# AAX – Ansible Automation Platform Alternative

[![CI](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml)
[![Release](https://github.com/kpeacocke/AAX/actions/workflows/release.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/release.yml)

> **Note:** This project is maintained independently. While the author current works at Red Hat, AAX is not an official Red Hat project, product, or service. For production use, Red Hat recommends their commercial [Ansible Automation Platform](https://www.ansible.com/products/automation-platform). And so does the author.

A containerised, open-source alternative to Red Hat Ansible Automation Platform, built from upstream projects and run with Docker Compose. Where practical, AAX uses official upstream runtime images and keeps project-specific customization at the Compose/settings layer.

The project now uses a single, flattened [docker-compose.yml](docker-compose.yml) for all services, with Compose profiles for the controller, hub, and EDA stacks.

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

For a strict AAP-to-AAX component mapping, implementation status, and gap analysis, see [COMPONENTS.md](COMPONENTS.md).

## Quick Start

```bash
git clone https://github.com/kpeacocke/AAX.git
cd AAX
cp .env.example .env

docker compose --profile controller up -d
```

- **AWX UI:** <http://localhost:18080>
- **Admin password:**

  ```bash
  docker compose --profile controller logs awx-web | grep "Admin password"
  ```

To run the hub stack:

```bash
docker compose --profile hub up -d
```

Profile note:

- If `COMPOSE_PROFILES` is set in `.env`, Docker Compose combines it with any CLI `--profile` flags.
- To run a single stack predictably (for example hub-only), keep `COMPOSE_PROFILES` empty and pass explicit `--profile` flags in the command.

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

Controller note:

- `awx-web` and `awx-task` default to the official `quay.io/ansible/awx:24.6.1` image.
- If you switch from an older custom AWX image, redeploy so the controller services pull the official image.
- Public AWX traffic should terminate at the gateway on `GATEWAY_PORT`; `AWX_WEB_PORT` remains useful for local direct validation.

## Portainer Deployment (Synology/NAS)

Use Portainer Git repository stack mode with the single compose file.

1. Stack source:

- Repository URL: your AAX fork/repo
- Compose path: docker-compose.yml

1. Required Portainer environment variables (minimum):

- COMPOSE_PROFILES=controller,hub
- HOST_BIND=127.0.0.1
- DATABASE_PASSWORD=your-awx-db-password
- SECRET_KEY=your-awx-secret-key
- AWX_ADMIN_PASSWORD=your-awx-admin-password
- HUB_DB_PASSWORD=your-hub-db-password
- HUB_ADMIN_PASSWORD=your-hub-admin-password
- GALAXY_SECRET_KEY=your-galaxy-secret-key
- PULP_SECRET_KEY=your-pulp-secret-key

1. Synology reverse proxy hostnames (recommended):

- ALLOWED_HOSTS=awx.example.com,hub.example.com,localhost,127.0.0.1
- AWX_CSRF_TRUSTED_ORIGINS=https://awx.example.com,https://hub.example.com
- GALAXY_ALLOWED_HOSTS=hub.example.com,galaxy-ng,gateway,localhost,127.0.0.1
- PULP_ALLOWED_HOSTS=awx.example.com,hub.example.com,localhost,127.0.0.1,[::1],pulp-api,pulp-content,galaxy-ng,gateway
- PULP_CONTENT_ORIGIN=https://awx.example.com
- PULP_ANSIBLE_API_HOSTNAME=https://hub.example.com

1. Synology DSM Login Portal reverse proxy rules:

- Rule 1: https://awx.example.com -> http://127.0.0.1:18088
- Rule 2: https://hub.example.com -> http://127.0.0.1:15001

1. Expected public health signals after deployment:

- `https://awx.example.com/api/v2/ping/` returns `200` when controller traffic is correctly routed through the gateway.
- `https://hub.example.com/api/galaxy/` returns `403` before login; this is a healthy unauthenticated hub response.
- Pulp remains gateway-routed under the AWX hostname, for example `https://awx.example.com/pulp/api/v3/` and `https://awx.example.com/pulp/content/`.

1. Certificates in DSM:

- Create or import certificates for awx.example.com and hub.example.com in Control Panel -> Security -> Certificate.
- Assign each certificate to the matching reverse proxy rule.

1. Deploy and monitor:

- Portainer builds local images during stack deployment.
- After changes, use Update the stack and Re-pull image and redeploy.
- Check container health before testing URLs.

Operational notes:

- Keep COMPOSE_PROFILES empty in .env for local CLI runs, then set profiles explicitly in Portainer variables.
- Do not expose raw Pulp ports on the router.
- Keep HOST_BIND=127.0.0.1 when DSM reverse proxy is on the same NAS.
- After editing stack variables in Portainer, use re-pull and redeploy so stale environment values do not survive the update.

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
