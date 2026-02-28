# Rate Limiting Configuration

This guide explains how to add rate limiting to AAX services using Traefik.

## Why Rate Limiting?

Rate limiting protects your AAX services from:

- **Brute force attacks** (password guessing)
- **DoS attacks** (resource exhaustion)
- **API abuse** (uncontrolled automation access)
- **Credential stuffing** (large-scale account takeover)

## Option 1: Traefik + Rate Limiting (Production)

### 1. Add Traefik to docker-compose.yml

```yaml
services:
  traefik:
    image: traefik:v3.2
    ports:
      - "80:80"
      - "443:443"
      - "8081:8080"  # Traefik dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
      - ./acme.json:/acme.json
    command:
      - "--api.dashboard=true"
      - "--api.debug=true"
    networks:
      - ansible
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
```

### 2. Create traefik.yml

```yaml
global:
  checkNewVersion: true
  sendAnonymousUsage: false

entryPoints:
  web:
    address: ":80"
    http:
      middlewares:
        - rate-limit@file
      redirections:
        entrypoint:
          scheme: https
          permanent: true
  websecure:
    address: ":443"
    http:
      middlewares:
        - rate-limit@file
      tls:
        certResolver: letsencrypt

api:
  dashboard: true
  debug: true

certificatesResolvers:
  letsencrypt:
    acme:
      email: "admin@example.com"
      storage: acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: ansible
  file:
    filename: traefik-dynamic.yml
    watch: true
```

### 3. Create traefik-dynamic.yml (Rate Limiting Rules)

```yaml
http:
  middlewares:
    rate-limit:
      rateLimit:
        average: 100          # 100 requests per second (average)
        burst: 50             # Allow burst up to 50 requests
        period: 1s

    # Strict limits for login endpoints
    auth-rate-limit:
      rateLimit:
        average: 10           # 10 requests per second on auth
        burst: 5
        period: 1s

  routers:
    awx-web:
      rule: "Host(`awx.localhost`)"
      service: awx-web
      entryPoints:
        - websecure
      middlewares:
        - auth-rate-limit    # Stricter limit for auth
      tls: {}

    awx-api:
      rule: "Host(`api.awx.localhost`)"
      service: awx-web
      entryPoints:
        - websecure
      middlewares:
        - rate-limit
      tls: {}

    galaxy:
      rule: "Host(`galaxy.localhost`)"
      service: galaxy-ng
      entryPoints:
        - websecure
      middlewares:
        - auth-rate-limit
      tls: {}

  services:
    awx-web:
      loadBalancer:
        servers:
          - url: "http://awx-web:8052"
    galaxy-ng:
      loadBalancer:
        servers:
          - url: "http://galaxy-ng:8000"
```

### 4. Update docker-compose.yml service labels

```yaml
services:
  awx-web:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.awx-web.rule=Host(`awx.localhost`)"
      - "traefik.http.services.awx-web.loadbalancer.server.port=8052"
```

### 5. Start with Traefik

```bash
docker compose up -d traefik awx-web
```

Access:

- AWX: <http://awx.localhost>
- Traefik Dashboard: <http://localhost:8081>

## Option 2: nginx + Rate Limiting (Simpler Alternative)

### 1. Create nginx.conf

```nginx
upstream awx {
    server awx-web:8052;
}

upstream galaxy {
    server galaxy-ng:8000;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=awx_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=galaxy_limit:10m rate=10r/s;

server {
    listen 80;
    server_name awx.localhost;

    location / {
        limit_req zone=awx_limit burst=5 nodelay;
        proxy_pass http://awx;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name galaxy.localhost;

    location / {
        limit_req zone=galaxy_limit burst=5 nodelay;
        proxy_pass http://galaxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Add to docker-compose.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - awx-web
      - galaxy-ng
    networks:
      - ansible
```

## Option 3: Application-Level Rate Limiting (AWX/Galaxy NG)

Add to `.env`:

```bash
# AWX rate limiting
AWX_ALLOWED_HOSTS=localhost,127.0.0.1,awx.example.com
AWX_BROADCAST_WEBSOCKET_BUFSIZE=32000

# Celery rate limiting
CELERY_BROKER_POOL_LIMIT=10
CELERY_WORKER_PREFETCH_MULTIPLIER=4
```

## Testing Rate Limiting

```bash
# Test with Apache Bench
ab -n 1000 -c 100 http://awx.localhost/

# Test with wrk
wrk -t12 -c400 -d30s http://awx.localhost/

# Monitor with watch
watch -n 1 'netstat -an | grep ESTABLISHED | wc -l'
```

## Monitoring Rate Limit Hits

### Traefik

Access dashboard: <http://localhost:8081>

### nginx

Check logs:

```bash
docker compose logs -f nginx | grep "limiting requests"
```

## Best Practices

1. **Protect Authentication Endpoints**: Stricter limits on `/api/login`, `/accounts/login`
2. **Monitor and Adjust**: Start conservative, loosen as needed
3. **Use Redis Cluster**: For distributed rate limiting across multiple instances
4. **Log Violations**: Track and audit rate limit violations
5. **Whitelist Trust Proxies**: Allow internal monitoring without limits
6. **Document Limits**: Inform API users of rate limits in docs

## Resources

- [Traefik Middleware - Rate Limiting](https://doc.traefik.io/traefik/middlewares/http/ratelimit/)
- [nginx Rate Limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html)
- [OWASP Rate Limiting](https://owasp.org/www-community/attacks/Rate_limiting)
