# Private Automation Hub

This directory contains the Docker Compose configuration for running a Private Automation Hub using Galaxy NG (Ansible content server) and Pulp (content management backend).

## Architecture

The hub stack consists of:

- **galaxy-ng** - Ansible Galaxy Next Generation web UI and API
- **pulp-api** - Pulp content management API
- **pulp-content** - Pulp content delivery service
- **pulp-worker** - Pulp background task worker
- **hub-postgres** - PostgreSQL database for hub data
- **hub-redis** - Redis cache and message broker

### Design Decision: Building Galaxy NG from Source

This hub stack builds Galaxy NG from the official Ansible repository (`github.com/ansible/galaxy_ng`) using the latest stable version. This aligns with AAX's philosophy of building all components from source.

**Why Galaxy NG + Pulp:**

1. **Official Upstream** - Galaxy NG is the open-source version of AAP Private Automation Hub
2. **Content Management** - Pulp provides robust content lifecycle management
3. **Collection Hosting** - Host and distribute Ansible collections privately
4. **Execution Environment Registry** - Store custom EE container images
5. **No External Dependencies** - Removes dependency on public Galaxy or external registries

**Trade-offs:**

- **Complexity** - Multiple services (pulp-api, pulp-content, pulp-worker)
- **Resources** - Requires additional CPU/memory (recommend 4GB+)
- **Maintenance** - Updates require coordinating Galaxy NG and Pulp versions

## Prerequisites

1. Docker Engine 20.10 or later
2. Docker Compose 2.0 or later
3. Minimum 4GB RAM allocated to Docker
4. AAX core services running (optional for standalone use)

## Quick Start

### 1. Configure Environment Variables (Optional)

```bash
cd /workspaces/AAX
cp .env.example .env
# Edit .env with your specific configuration
```

Key environment variables for the hub:

```bash
# Hub admin credentials
export HUB_ADMIN_PASSWORD=changeme

# Database configuration
export HUB_DB_PASSWORD=hubpassword

# Galaxy NG configuration
export GALAXY_SIGNATURE_UPLOAD_ENABLED=false
export GALAXY_REQUIRE_CONTENT_APPROVAL=true
export GALAXY_AUTO_SIGN_COLLECTIONS=false

# Pulp configuration
export PULP_CONTENT_ORIGIN=http://localhost:24816
export PULP_ANSIBLE_API_HOSTNAME=http://localhost:5001
```

### 2. Start the Hub Stack

```bash
# From the AAX root directory
docker compose -f docker-compose.hub.yml up -d
```

### 3. Access the Hub Interface

- **Galaxy NG UI**: <http://localhost:5001>
- **API Root**: <http://localhost:5001/api/galaxy/>
- **Pulp API**: <http://localhost:24817/pulp/api/v3/>
- **Content Delivery**: <http://localhost:24816>

Default credentials:

- Username: `admin`
- Password: (set via `HUB_ADMIN_PASSWORD` or default: `changeme`)

### 4. Verify Installation

```bash
# Check service health
docker compose -f docker-compose.hub.yml ps

# View logs
docker compose -f docker-compose.hub.yml logs -f

# Test API access
curl http://localhost:5001/api/galaxy/
```

## Configuration

### Publishing Collections

#### Via ansible-galaxy CLI

```bash
# Configure ansible-galaxy to use your private hub
cat > ~/.ansible.cfg << EOF
[galaxy]
server_list = private_hub

[galaxy_server.private_hub]
url=http://localhost:5001/api/galaxy/
token=<your-api-token>
EOF

# Build and publish a collection
ansible-galaxy collection build
ansible-galaxy collection publish namespace-collection-1.0.0.tar.gz
```

#### Via UI

1. Navigate to <http://localhost:5001>
2. Log in with admin credentials
3. Go to "Collections" → "Upload Collection"
4. Upload your `.tar.gz` collection archive

### Content Approval Workflow

If `GALAXY_REQUIRE_CONTENT_APPROVAL=true`:

1. Collections are uploaded to the "staging" repository
2. Administrators review content in the UI
3. Approved collections move to the "published" repository
4. Users can only install from "published"

To approve a collection:

```bash
# Via API
curl -X POST http://localhost:5001/api/galaxy/v3/collections/namespace/name/versions/1.0.0/move/published/ \
  -H "Authorization: Token <your-api-token>"
```

### Execution Environment Registry

Galaxy NG can also serve as a container registry for execution environments.

#### Push an EE to the Hub

```bash
# Tag your EE image
docker tag aax/ee-base:latest localhost:5001/ee-base:latest

# Log in to the registry
docker login localhost:5001
# Username: admin
# Password: <HUB_ADMIN_PASSWORD>

# Push the image
docker push localhost:5001/ee-base:latest
```

#### Pull from the Hub

```bash
docker pull localhost:5001/ee-base:latest
```

## Integration with AWX

To configure AWX to use your private hub:

### 1. Add Organization Galaxy Credentials

In AWX UI:

1. Navigate to "Resources" → "Credentials"
2. Create new credential:
   - **Name**: Private Hub Token
   - **Type**: Ansible Galaxy/Automation Hub API Token
   - **Galaxy Server URL**: `http://galaxy-ng:5001/api/galaxy/`
   - **Token**: (generate from hub UI)

### 2. Configure Project

1. Create/edit a project in AWX
2. In "Source Control" settings:
   - Select your Galaxy credential
   - Add `requirements.yml` with private collections

Example `requirements.yml`:

```yaml
---
collections:
  - name: namespace.collection
    version: ">=1.0.0"
    source: http://galaxy-ng:5001/api/galaxy/
```

### 3. Update Docker Compose Network

To connect AWX and Hub stacks:

```bash
# Start both stacks on the same network
docker compose -f docker-compose.hub.yml -f docker-compose.controller.yml up -d
```

Or modify `docker-compose.controller.yml` to include:

```yaml
networks:
  awx-network:
    external: true
    name: aax_ansible
```

## API Usage Examples

### List Collections

```bash
curl http://localhost:5001/api/galaxy/v3/collections/
```

### Get Collection Details

```bash
curl http://localhost:5001/api/galaxy/v3/collections/namespace/collection/
```

### Upload Collection

```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:5001/api/galaxy/v3/auth/token/ \
  -d '{"username":"admin","password":"changeme"}' \
  -H "Content-Type: application/json" | jq -r .token)

# Upload collection
curl -X POST http://localhost:5001/api/galaxy/v3/artifacts/collections/ \
  -H "Authorization: Token $TOKEN" \
  -F "file=@namespace-collection-1.0.0.tar.gz"
```

### Pulp API Examples

```bash
# List repositories
curl http://localhost:24817/pulp/api/v3/repositories/ansible/ansible/

# List content
curl http://localhost:24817/pulp/api/v3/content/ansible/collection_versions/
```

## Management Commands

```bash
# Start hub services
docker compose -f docker-compose.hub.yml up -d

# Stop hub services
docker compose -f docker-compose.hub.yml down

# View logs
docker compose -f docker-compose.hub.yml logs -f

# Check status
docker compose -f docker-compose.hub.yml ps

# Restart services
docker compose -f docker-compose.hub.yml restart

# Clean all hub data (destructive!)
docker compose -f docker-compose.hub.yml down -v
```

## Database Migrations

When updating Galaxy NG or Pulp:

```bash
# Run Galaxy NG migrations
docker compose -f docker-compose.hub.yml exec galaxy-ng django-admin migrate --no-input

# Run Pulp migrations
docker compose -f docker-compose.hub.yml exec pulp-api pulpcore-manager migrate --no-input
```

## Backup and Restore

### Backup

```bash
# Backup database
docker compose -f docker-compose.hub.yml exec hub-postgres pg_dump -U galaxy hub > hub_backup.sql

# Backup uploaded content
docker run --rm -v aax_hub_pulp_storage:/data -v $(pwd):/backup \
  alpine tar czf /backup/hub_content_backup.tar.gz -C /data .
```

### Restore

```bash
# Restore database
cat hub_backup.sql | docker compose -f docker-compose.hub.yml exec -T hub-postgres psql -U galaxy hub

# Restore content
docker run --rm -v aax_hub_pulp_storage:/data -v $(pwd):/backup \
  alpine tar xzf /backup/hub_content_backup.tar.gz -C /data
```

## Troubleshooting

### Collections Won't Upload

**Problem**: Error when uploading collections

**Solutions**:

1. Check disk space: `df -h`
2. Verify pulp-worker is running: `docker compose -f docker-compose.hub.yml ps`
3. Check pulp-worker logs: `docker compose -f docker-compose.hub.yml logs pulp-worker`
4. Ensure collection tarball is valid: `ansible-galaxy collection build --force`

### Content Not Appearing

**Problem**: Uploaded content doesn't show in UI

**Solutions**:

1. Wait for pulp-worker to process (check logs)
2. Verify repository sync: Check Pulp API
3. Clear Redis cache: `docker compose -f docker-compose.hub.yml restart hub-redis`

### Cannot Connect from AWX

**Problem**: AWX can't reach the hub

**Solutions**:

1. Ensure both stacks use the same Docker network
2. Use service name (`galaxy-ng`) not `localhost` in AWX
3. Check network connectivity: `docker compose exec awx_web ping galaxy-ng`

### Performance Issues

**Solutions**:

1. Increase pulp-worker replicas in compose file
2. Allocate more memory to PostgreSQL
3. Use external S3-compatible storage for artifacts
4. Enable Redis persistence for caching

## Production Considerations

1. **Use External PostgreSQL** - Deploy a managed database service
2. **Enable HTTPS** - Use a reverse proxy (nginx, Traefik, Caddy)
3. **Object Storage** - Configure S3/MinIO for artifact storage
4. **Update Credentials** - Change all default passwords
5. **Content Signing** - Enable collection signing with GPG keys
6. **Configure LDAP/SSO** - Integrate with your identity provider
7. **Set Up Monitoring** - Monitor Pulp workers and task queue
8. **Enable Backups** - Automate database and artifact backups
9. **Scale Workers** - Run multiple pulp-worker containers
10. **Rate Limiting** - Configure nginx rate limiting for API

## Resources

- [Galaxy NG Documentation](https://github.com/ansible/galaxy_ng)
- [Pulp Documentation](https://docs.pulpproject.org/)
- [Ansible Galaxy CLI](https://docs.ansible.com/ansible/latest/cli/ansible-galaxy.html)
- [Collection Publishing Guide](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections_distributing.html)
