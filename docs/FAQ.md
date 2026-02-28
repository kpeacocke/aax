# Frequently Asked Questions

## Getting Started

### Q: How do I stop AAX without losing data?

**A:** Use `docker compose stop` instead of `down`:

```bash
# Stop containers (preserves volumes and data)
docker compose stop

# Restart later
docker compose start

# Full shutdown (removes containers but keeps volumes)
docker compose down
```

---

### Q: How long does AWX take to start?

**A:** First boot typically takes **2-3 minutes** due to:

- Database migrations
- Static asset collection  
- User initialization

Subsequent startups are ~30-60 seconds. Watch logs:

```bash
docker compose logs -f awx-web | grep -i "ready\|listen\|migrate"
```

---

### Q: How do I reset AWX admin password?

**A:** Reset via Django shell:

```bash
docker compose exec awx-web awx-manage changepassword admin
```

Or set during deployment:

```bash
export AWX_ADMIN_PASSWORD="your-secure-password"  # pragma: allowlist secret
docker compose up -d
```

---

### Q: Can I use this in production?

**A:** Yes, but **Red Hat recommends their commercial Ansible Automation Platform** for production. AAX is great for:

- Development and testing
- Learning Ansible automation
- Self-hosted labs
- Non-critical automation

For mission-critical automation, consider commercial support from Red Hat.

---

## Configuration & Customization

### Q: How do I add custom Python packages to execution environments?

**A:** Create an execution environment definition:

```bash
# Create EE definition
cat > execution-environment.yml <<EOF
---
version: 3
images:
  base_image:
    name: aax/ee-base:latest

dependencies:
  python: requirements.txt
  system: bindep.txt
  galaxy: requirements.yml
EOF

# Create requirements files
cat > requirements.txt <<EOF
requests==2.31.0
netaddr==0.9.0
EOF

# Build
docker compose exec ee-builder ansible-builder build \
  -f execution-environment.yml \
  -t my-custom-ee:latest
```

---

### Q: How do I modify the AWX configuration?

**A:** Edit `.env` file:

```bash
cp .env.example .env
# Edit .env with your settings
docker compose restart awx-web
```

Or mount custom configuration:

```bash
docker compose exec awx-web cat /etc/tower/settings.py > /tmp/settings.py
# Edit /tmp/settings.py
docker compose cp /tmp/settings.py awx-web:/etc/tower/settings.py
```

---

### Q: How do I change the Docker Compose port mappings?

**A:** Create `docker-compose.override.yml`:

```yaml
services:
  awx-web:
    ports:
      - "9000:8052"  # Use port 9000 instead of 8080
```

---

## Troubleshooting

### Q: AWX shows "502 Bad Gateway"

**A:** AWX might still be starting. Check logs:

```bash
docker compose logs awx-web | tail -50
```

Wait 2-3 minutes for first boot, then try again.

---

### Q: Can't connect to Galaxy NG / Pulp

**A:** Verify services are running:

```bash
docker compose ps

# If stopped, start hub profile
docker compose --profile hub up -d
```

---

### Q: Docker socket permission denied in ee-builder

**A:** Fix socket permissions:

```bash
docker compose exec ee-builder id
# Should show: uid=1000(ansible) gid=1000(ansible) groups=1000(ansible),999(docker)

# If not in docker group, restart
docker compose restart ee-builder
```

---

### Q: Health checks show "unhealthy"

**A:** Wait 30 seconds for health checks to stabilize, then verify:

```bash
docker compose exec ee-base python3 -c "import ansible; print('OK')"
docker compose exec ee-builder ansible-builder --version
docker compose exec dev-tools ansible-navigator --version
```

---

### Q: I'm running out of disk space

**A:** Check Docker volumes:

```bash
docker system df

# Clean up unused volumes
docker volume prune -f

# Check individual image sizes
docker images --human-readable --format "{{.Size}}\t{{.Repository}}:{{.Tag}}"
```

---

## Performance & Optimization

### Q: How can I improve AWX performance?

**A:** Increase resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: "4"      # Increase from 2
      memory: 4G     # Increase from 2G
    reservations:
      cpus: "2"
      memory: 2G
```

---

### Q: Can I scale deployments horizontally?

**A:** For Docker Compose, you can replicate services:

```bash
docker compose up -d --scale dev-tools=3
```

For Kubernetes, update deployment replicas:

```bash
kubectl scale -n aax deployment/dev-tools --replicas=3
```

---

### Q: What's the recommended hardware?

**A:** Minimum:

- 4 GB RAM
- 20 GB disk space
- 2 CPU cores

Recommended for multiple projects:

- 8+ GB RAM
- 50+ GB disk space
- 4+ CPU cores

---

## Integration & API

### Q: How do I access the AWX API?

**A:** Get an auth token:

```bash
curl -k -u admin:password \
  http://localhost:8080/api/v2/auth-tokens/ \
  -d '{}' | jq '.token'
```

Use token for API calls:

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8080/api/v2/inventories/
```

---

### Q: Can I add custom credentials to AWX?

**A:** Use AWX UI or API:

Via UI:

1. Credentials → New Credential
2. Select credential type
3. Fill in details

Via API:

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/v2/credentials/ \
  -d '{
    "name": "My SSH Key",
    "credential_type": 1,  # SSH
    "inputs": {"ssh_key_data": "..."}
  }'
```

---

### Q: How do I trigger automation from external systems?

**A:** Use job templates and webhooks:

1. Create job template in AWX
2. Enable webhook
3. Get webhook URL: `Settings → Webhooks`
4. Call webhook:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"extra_vars": {"key": "value"}}' \
  http://localhost:8080/api/v2/job_templates/1/launch/
```

---

## Kubernetes Deployment

### Q: Can I deploy AAX to Kubernetes?

**A:** Yes! Use manifests in `k8s/`:

```bash
kubectl apply -k k8s/
```

See [k8s/K8S.md](../k8s/K8S.md) for details.

---

### Q: What's the difference between Docker Compose and Kubernetes?

**A:**

| Feature                | Docker Compose       | Kubernetes          |
| ---------------------- | -------------------- | ------------------- |
| **Best for**           | Development, testing | Production, scaling |
| **HA Support**         | No                   | Yes (replicas)      |
| **Load balancing**     | No                   | Yes                 |
| **Persistent storage** | Local volumes        | PersistentVolumes   |
| **Networking**         | Bridge networks      | Service discovery   |
| **Rolling updates**    | Manual               | Automatic           |
| **Resource isolation** | Limited              | Full cgroups        |

---

## Contributing

### Q: How do I contribute fixes or features?

**A:** See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full process:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Apply your changes
4. Push and create a pull request

---

### Q: What are the coding standards?

**A:**

- **Python:** Black, isort, pylint
- **YAML:** yamllint, 2-space indentation
- **Shell:** shellcheck
- **Dockerfile:** hadolint
- **Markdown:** markdownlint

All checked automatically via pre-commit hooks.

---

## Support & Community

### Q: Where do I report bugs?

**A:** Open an issue on [GitHub Issues](https://github.com/kpeacocke/AAX/issues) with:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (`docker compose logs`)
- System info (OS, Docker version)

---

### Q: Where can I ask questions?

**A:** Use [GitHub Discussions](https://github.com/kpeacocke/AAX/discussions) for:

- How-to questions
- Best practices
- General feedback
- Ideas for improvements

---

### Q: Is there a community wiki?

**A:** Yes! Check the [GitHub Wiki](https://github.com/kpeacocke/AAX/wiki) for:

- Community guides
- Integration examples
- Troubleshooting tips
- Advanced configurations

---

## License & Legal

### Q: Can I use AAX commercially?

**A:** AAX itself is Apache 2.0 licensed. Check individual component licenses:

- AWX: Apache 2.0
- Galaxy NG: Apache 2.0
- Pulp: GPLv2
- Ansible: GPLv3

For commercial use, consult legal counsel.

---

### Q: Is this affiliated with Red Hat or Ansible?

**A:** No. AAX is an independent, community-maintained project. Red Hat recommends their commercial Ansible Automation Platform for production use.

---

## More Help

- 📖 **Full Docs:** See [docs/INDEX.md](../docs/INDEX.md)
- 🐛 **Bugs:** [GitHub Issues](https://github.com/kpeacocke/AAX/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/kpeacocke/AAX/discussions)
- 📝 **Wiki:** [GitHub Wiki](https://github.com/kpeacocke/AAX/wiki)
- 🔒 **Security:** See [SECURITY.md](../SECURITY.md)
