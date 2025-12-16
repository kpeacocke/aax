# Security Policy

## Supported Versions

We take security seriously and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Update Policy

- **Critical vulnerabilities**: Patches released within 24-48 hours
- **High severity**: Patches released within 1 week
- **Medium/Low severity**: Addressed in the next scheduled release

## Reporting a Vulnerability

We appreciate responsible disclosure of security vulnerabilities. Please help us keep AAX and its users safe.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security vulnerabilities by:

1. **Email**: Send details to [krpeacocke@gmail.com](mailto:krpeacocke@gmail.com)
   - Use PGP encryption if possible (key available at the end of this document)
   - Include "AAX Security" in the subject line

2. **GitHub Security Advisories**: Use the [GitHub Security Advisory](https://github.com/kpeacocke/AAX/security/advisories/new) feature (preferred)

### What to Include

Please provide as much information as possible:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** of the vulnerability
- **Affected versions** (if known)
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up

**Example Report:**

```text
Subject: AAX Security - Authentication Bypass in AWX Integration

Description:
An authentication bypass vulnerability exists in the AWX integration
component that allows unauthorized access to administrative functions.

Steps to Reproduce:
1. Deploy AAX with default configuration
2. Send a crafted request to /api/v2/admin endpoint
3. Access is granted without valid credentials

Impact:
Attackers can gain administrative access to the AWX instance,
potentially compromising all automation workflows and credentials.

Affected Versions:
AAX v1.2.0 through v1.4.1

Suggested Fix:
Implement proper authentication checks in the middleware layer
before processing administrative API requests.

Contact:
researcher@example.com
```

### What to Expect

1. **Acknowledgment**: Within 24 hours of your report
2. **Initial Assessment**: Within 72 hours
3. **Regular Updates**: At least weekly on our progress
4. **Coordinated Disclosure**: We'll work with you on timing
5. **Recognition**: With your permission, credit in security advisory

### Response Timeline

- **24 hours**: Acknowledgment of receipt
- **72 hours**: Initial assessment and severity classification
- **7 days**: Regular status updates
- **30-90 days**: Target resolution timeframe (depending on severity)

## Security Best Practices

### Deployment Security

#### 1. Change Default Credentials

```bash
# Generate strong passwords
openssl rand -base64 32

# Update .env file immediately after first deployment
AAX_ADMIN_PASSWORD=<strong-random-password>
POSTGRES_PASSWORD=<strong-random-password>
SECRET_KEY=<strong-random-key>
```

#### 2. Enable HTTPS

```yaml
# Use a reverse proxy (nginx, Traefik, Caddy)
# Example nginx configuration
server {
    listen 443 ssl http2;
    server_name aax.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3. Network Isolation

```bash
# Use Docker networks to isolate services
docker network create --driver bridge aax_internal

# Expose only necessary ports
# Bind to localhost only for non-public services
ports:
  - "127.0.0.1:5432:5432"  # PostgreSQL - local only
  - "8080:8080"            # AWX Web - public
```

#### 4. Restrict File Permissions

```bash
# Secure environment files
chmod 600 .env
chmod 600 certs/*.key

# Secure SSH keys if used
chmod 600 keys/*_rsa
chmod 644 keys/*_rsa.pub
```

#### 5. Enable Authentication

Configure external authentication in AWX:

- LDAP/Active Directory
- SAML 2.0
- OAuth 2.0 / OpenID Connect

#### 6. Regular Updates

```bash
# Update container images regularly
docker-compose pull
docker-compose up -d

# Subscribe to security advisories
# Watch this repository for updates
```

#### 7. Secure Secrets Management

```bash
# Use Docker secrets or external secret managers
# Never commit secrets to version control

# Example with Docker secrets
docker secret create postgres_password ./postgres_password.txt

# Reference in docker-compose.yml
secrets:
  - postgres_password
```

#### 8. Enable Audit Logging

```yaml
# Configure comprehensive logging
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

# Ship logs to SIEM or log aggregation platform
```

#### 9. Implement Firewall Rules

```bash
# Example using ufw (Ubuntu)
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 443/tcp   # HTTPS
ufw enable

# Example using firewalld (RHEL/CentOS)
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
```

#### 10. Regular Backups

```bash
# Automated encrypted backups
# Store backups in secure, separate location
# Test restore procedures regularly

# Example backup script
docker-compose exec postgres pg_dump -U awx awx | \
  gpg --encrypt --recipient admin@example.com > \
  backup-$(date +%Y%m%d).sql.gpg
```

### Container Security

#### Scan Images for Vulnerabilities

```bash
# Using Trivy
trivy image aax/awx:latest

# Using Snyk
snyk container test aax/awx:latest

# Using Clair
clairctl analyze aax/awx:latest
```

#### Run as Non-Root User

```dockerfile
# In Dockerfile
RUN useradd -r -u 1000 -g appgroup appuser
USER appuser
```

#### Use Read-Only Filesystems

```yaml
# In docker-compose.yml
services:
  awx_web:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### Compliance

This project aims to align with:

- **OWASP Top 10** security risks
- **CIS Docker Benchmark**
- **NIST Cybersecurity Framework**
- **GDPR** data protection requirements (where applicable)

## Known Security Considerations

### Supply Chain Security

- All base images are pulled from official sources
- Image digests are pinned in production deployments
- Dependencies are regularly scanned for vulnerabilities
- Software Bill of Materials (SBOM) available for each release

### Data Protection

- Secrets are encrypted at rest in the database
- TLS encryption for data in transit
- Support for external secret management systems
- Audit logging of all access to sensitive data

### Access Control

- Role-Based Access Control (RBAC) implemented
- Principle of least privilege enforced
- Support for multi-factor authentication
- Session timeout and management

## Security Advisories

Security advisories are published at:

- [GitHub Security Advisories](https://github.com/kpeacocke/AAX/security/advisories)
- Project website security page
- Mailing list announcements

Subscribe to security notifications:

- Watch this repository's security advisories
- Join our security mailing list (link)

## Security Testing

We perform:

- **Static Application Security Testing (SAST)** on every commit
- **Dependency scanning** using automated tools
- **Container scanning** for known vulnerabilities
- **Secret scanning** to prevent credential leaks
- **Periodic penetration testing** by third parties

## Bug Bounty Program

We currently do not have a formal bug bounty program, but we recognize and credit security researchers who responsibly disclose vulnerabilities:

- Public acknowledgment (with permission)
- Credit in security advisories
- Listed in our security hall of fame

## Hall of Fame

We thank the following security researchers for their responsible disclosure:

<!-- This section will be updated as vulnerabilities are reported and fixed -->

## PGP Key

```text
-----BEGIN PGP PUBLIC KEY BLOCK-----
[PGP Public Key will be added here]
-----END PGP PUBLIC KEY BLOCK-----
```

## Additional Resources

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [AWX Security Documentation](https://github.com/ansible/awx/blob/devel/SECURITY.md)
- [Ansible Security Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html#best-practices-for-variables-and-vaults)

## Questions?

For non-security questions, please use:

- GitHub Discussions
- GitHub Issues (for non-security bugs)

For security questions that don't involve a vulnerability:

- Email: <krpeacocke@gmail.com>
- Use "AAX Security Question" in the subject

---

**Last Updated**: December 2025

This security policy is subject to change. Please check back regularly for updates.
