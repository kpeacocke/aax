# Network Boundaries

AAX defaults to a minimal external attack surface with localhost-first publishing.

## Default Exposure Model

- Gateway-first for shared APIs and web access.
- Host-published ports are localhost-bound by default via `HOST_BIND=127.0.0.1`.
- Raw Pulp API/content ports are not published by default.

## Trust Zones

- Host-local edge: published controller/hub/eda/gateway ports on localhost.
- Internal service mesh: compose networks and Kubernetes ClusterIP services.
- Secrets boundary: runtime secrets in env/secret providers, not static plaintext in production overlays.

## Debug-Only Exposure

Use `docker-compose.debug-exposure.yml` only for isolated lab debugging.

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.debug-exposure.yml \
  --profile controller --profile hub --profile eda up -d
```

This override intentionally binds edge ports to `0.0.0.0` and should not be used in shared or production-like environments.
