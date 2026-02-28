# AWX Controller Stack

This directory contains the Docker Compose configuration for running AWX (Ansible Automation Platform controller) with Receptor mesh networking.

## Architecture

The stack consists of:

- **awx-web** - AWX web interface and API server
- **awx-task** - AWX task dispatcher and job runner
- **awx-postgres** - PostgreSQL database for AWX data
- **awx-redis** - Redis cache and message broker
- **awx-receptor** - Receptor mesh node for distributed execution

### Design Decision: Building AWX from Source

This controller stack builds AWX from the official Ansible AWX source repository (`github.com/ansible/awx`) at version 24.6.1. This aligns with AAX's philosophy of building all components from source.

**Why Build from Source:**

1. **Consistency** - Matches the pattern used for execution environments (ee-base, ee-builder, dev-tools)
2. **Transparency** - Full visibility into what's running in your automation platform
3. **Customisation** - Ability to modify AWX behaviour if needed
4. **No Registry Dependencies** - Removes dependency on external Docker registries (Docker Hub, Quay.io)

**Trade-offs:**

- **Build Time** - Initial build takes 10-15 minutes as it clones and builds AWX
- **Maintenance** - Updates require rebuilding the image with a new AWX version tag
- **Complexity** - More moving parts than using pre-built images

The `images/awx/Dockerfile` builds AWX 24.6.1 from source, installs all Python dependencies, and creates custom entrypoint scripts for the web and task services.

## Prerequisites

1. Docker Engine 20.10 or later
2. Docker Compose 5.1.0 or later
3. Minimum 4GB RAM allocated to Docker
4. AAX execution environment images built:

  ```bash
  cd /workspaces/aax
  docker compose build
  ```

## Quick Start

### 1. Configure Environment Variables (Optional)

The controller stack uses environment variables for configuration. A `.env.example` file is provided in the root directory:

```bash
cd /workspaces/aax
cp .env.example .env
# Edit .env with your specific configuration
```

Key variables you may want to customise:

- `POSTGRES_PASSWORD` - PostgreSQL database password
- `AWX_ADMIN_PASSWORD` - AWX admin user password
- `SECRET_KEY` - AWX secret key for encryption
- `AWX_WEB_PORT` - Host port for AWX web interface (default: 8080)
- `AWX_RECEPTOR_PORT` - Host port for Receptor (default: 8888)

If you don't create a `.env` file, the stack will use default values.

### 2. Start the Controller Stack

```bash
cd /workspaces/aax
docker compose --profile controller up -d
```

### 3. Wait for Services to Initialise

AWX takes 2-3 minutes to initialise on first startup:

```bash
# Watch the logs
docker compose --profile controller logs -f awx-task

# Wait for this message:
# "System is ready"
```

### 4. Access the AWX Web Interface

- **URL**: <http://localhost:8080>
- **Username**: `admin`
- **Password**: `password`

> ⚠️ **Security Note**: Change the default password immediately in production!

## Running Your First Job

### Option 1: Via Web UI

1. Navigate to <http://localhost:8080> and log in
2. Go to **Resources** → **Templates**
3. Create a new **Job Template**:
   - **Name**: Hello World
   - **Job Type**: Run
   - **Inventory**: Demo Inventory (create if needed)
   - **Project**: Demo Project (create if needed)
   - **Execution Environment**: `aax/ee-base:latest`
   - **Playbook**: Select a playbook from your project
4. Click **Launch** to run the job

### Option 2: Via AWX CLI

Install AWX CLI:

```bash
pip install awxkit
```

Run a simple command:

```bash
# Configure AWX CLI
export TOWER_HOST=http://localhost:8080
export TOWER_USERNAME=admin
export TOWER_PASSWORD=password
export TOWER_VERIFY_SSL=false

# List available execution environments
awx execution_environments list

# Run an ad-hoc command
awx ad_hoc_commands create \
  --inventory 1 \
  --module_name debug \
  --module_args "msg='Hello from AWX!'" \
  --execution_environment 1
```

### Option 3: Simple Hello World Demo

Create a demo project and job:

```bash
# 1. Create a project directory
mkdir -p /tmp/awx-demo
cd /tmp/awx-demo

# 2. Create a simple playbook
cat > hello-world.yml <<EOF
---
- name: Hello World Playbook
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Print hello message
      debug:
        msg: "Hello from AWX using aax/ee-base:latest!"

    - name: Show Ansible version
      command: ansible --version
      register: ansible_version

    - name: Display version
      debug:
        var: ansible_version.stdout_lines
EOF

# 3. Create an inventory
cat > inventory.ini <<EOF
[local]
localhost ansible_connection=local
EOF

# 4. Copy files to AWX projects volume
docker cp . awx-task:/var/lib/awx/projects/demo/

# 5. Create and run via AWX CLI or Web UI
```

## Configuration

### Default Execution Environment

The controller is pre-configured to use `aax/ee-base:latest` as the default execution environment. This is set via:

```yaml
environment:
  DEFAULT_EXECUTION_ENVIRONMENT: aax/ee-base:latest
```

### Changing Admin Credentials

The recommended way to change credentials is using the `.env` file:

```bash
# Edit .env file in the root directory
AWX_ADMIN_USER=admin
AWX_ADMIN_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key
```

```yaml
environment:
  AWX_ADMIN_USER: ${AWX_ADMIN_USER:-admin}
  AWX_ADMIN_PASSWORD: ${AWX_ADMIN_PASSWORD:-your-secure-password}
  SECRET_KEY: ${SECRET_KEY:-your-secret-key}
```

### Database Credentials

For production, update the PostgreSQL credentials in your `.env` file:

```bash
DATABASE_PASSWORD=your-secure-db-password
```

Or edit the docker-compose file directly:

```yaml
awx-postgres:
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-your-secure-db-password}

awx-web:
  environment:
    DATABASE_PASSWORD: ${DATABASE_PASSWORD:-your-secure-db-password}
```

## Receptor Mesh

The included Receptor node enables distributed execution. To add execution nodes:

### Add External Execution Node

1. Deploy receptor on another host:

```yaml
services:
  receptor-node:
    image: quay.io/ansible/receptor:1.4.7
    command:
      - receptor
      - --config
      - /etc/receptor/receptor.conf
    volumes:
      - ./receptor-external.conf:/etc/receptor/receptor.conf:ro
```

1. Configure the node to peer with the controller:

```yaml
# receptor-external.conf
---
- node:
    id: execution-node-1

- tcp-peer:
  address: awx-receptor:8888

- work-command:
    worktype: ansible-runner
    command: ansible-runner
    params: worker
    allowruntimeparams: true
```

## Managing the Stack

### View Status

```bash
docker compose --profile controller ps
```

### View Logs

```bash
# All services
docker compose --profile controller logs -f

# Specific service
docker compose --profile controller logs -f awx-web
docker compose --profile controller logs -f awx-task
```

### Stop Services

```bash
docker compose --profile controller down
```

### Stop and Remove Data

```bash
docker compose --profile controller down -v
```

### Restart Services

```bash
docker compose --profile controller restart
```

## Troubleshooting

### AWX Not Starting

Check the task container logs:

```bash
docker compose --profile controller logs awx-task
```

Common issues:

- Database not ready - wait for postgres healthcheck to pass
- Migrations running - wait 2-3 minutes for first startup
- Port 8080 in use - change the port mapping

### Cannot Login

1. Check admin password in docker-compose.controller.yml
2. Reset password:

```bash
docker compose --profile controller exec awx-task awx-manage changepassword admin
```

### Jobs Not Running

1. Verify execution environment image exists:

```bash
docker images | grep aax/ee-base
```

1. Check receptor status:

```bash
docker compose --profile controller exec awx-receptor receptorctl --socket /var/lib/receptor/receptor.sock status
```

1. Ensure Docker socket is mounted and accessible

### Database Connection Errors

Verify PostgreSQL is running and healthy:

```bash
docker compose --profile controller exec awx-postgres pg_isready -U awx
```

## API Access

AWX provides a REST API at `/api/v2/`:

```bash
# Get API root
curl -u admin:password http://localhost:8080/api/v2/

# List jobs
curl -u admin:password http://localhost:8080/api/v2/jobs/

# Launch a job template (ID 1)
curl -X POST -u admin:password \
  http://localhost:8080/api/v2/job_templates/1/launch/ \
  -H "Content-Type: application/json"
```

## Backup and Restore

### Backup

```bash
# Backup database
docker compose --profile controller exec awx-postgres \
  pg_dump -U awx awx > awx-backup-$(date +%Y%m%d).sql

# Backup volumes
docker run --rm \
  -v awx_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/awx-volumes-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
# Restore database
docker compose --profile controller exec -T awx-postgres \
  psql -U awx awx < awx-backup-20231215.sql
```

## Production Considerations

1. **Use external PostgreSQL** - Deploy a managed database service
2. **Enable HTTPS** - Use a reverse proxy (nginx, Traefik)
3. **Update credentials** - Change all default passwords
4. **Configure LDAP/SAML** - Integrate with your identity provider
5. **Set up monitoring** - Prometheus metrics at `/api/v2/metrics`
6. **Enable backups** - Automate database and project backups
7. **Use secrets management** - Store credentials in Docker secrets or vault
8. **Scale workers** - Run multiple awx-task containers

## Integration with AAX

This controller stack uses the execution environments built in the main AAX project:

- **Base EE**: `aax/ee-base:latest` - Default execution environment
- **Builder**: `aax/ee-builder:latest` - For building custom EEs
- **Dev Tools**: `aax/dev-tools:latest` - For development and testing

To build custom execution environments within AWX:

1. Create an execution environment definition
2. Use the AWX API or UI to register `aax/ee-builder:latest`
3. Build and register custom EEs through AWX

## Next Steps

- Explore the AWX UI and familiarize yourself with resources
- Create custom execution environments with additional collections
- Set up LDAP/SAML authentication
- Configure external Receptor execution nodes
- Integrate with Git repositories for project management
- Set up webhooks for CI/CD integration

## Resources

- [AWX Documentation](https://ansible.readthedocs.io/projects/awx/en/latest/)
- [AWX GitHub](https://github.com/ansible/awx)
- [Receptor Documentation](https://receptor.readthedocs.io/)
- [Ansible Builder](https://ansible-builder.readthedocs.io/)
