# Endpoints and Profiles Canonical Reference

This is the canonical source for externally reachable endpoints and compose profile exposure defaults.

## Default Bind Policy

- Published ports are bound through `HOST_BIND`.
- Default bind is localhost only: `HOST_BIND=127.0.0.1`.
- Use `HOST_BIND=0.0.0.0` only when remote access is explicitly required.

## Compose Endpoint Defaults

| Service                | Profile(s)           | Host Variable       | Default Host Port | Container Port | URL                      |
| ---------------------- | -------------------- | ------------------- | ----------------- | -------------- | ------------------------ |
| AWX UI/API             | controller           | `AWX_WEB_PORT`      | `18080`           | `8052`         | `http://localhost:18080` |
| Receptor Mesh Listener | controller           | `AWX_RECEPTOR_PORT` | `18888`           | `8888`         | `tcp://localhost:18888`  |
| Unified Gateway        | controller, hub, eda | `GATEWAY_PORT`      | `18088`           | `8080`         | `http://localhost:18088` |
| Galaxy NG UI/API       | hub                  | `GALAXY_PORT`       | `15001`           | `8000`         | `http://localhost:15001` |
| EDA Controller         | eda                  | `EDA_PORT`          | `15000`           | `5000`         | `http://localhost:15000` |

Notes:

- `AWX_WEB_PORT` exposes the AWX container directly and is useful for local validation.
- `GATEWAY_PORT` is the preferred shared ingress for controller, Pulp, and optional EDA paths.
- `GALAXY_PORT` is the preferred direct hub endpoint for `/api/galaxy/` and login flows.

## Recommended Public Mapping

For Synology DSM reverse proxy or any equivalent TLS-terminating ingress:

- Route the AWX public hostname to `http://127.0.0.1:${GATEWAY_PORT}`.
- Route the hub public hostname to `http://127.0.0.1:${GALAXY_PORT}`.
- Keep `HOST_BIND=127.0.0.1` when the reverse proxy runs on the same host.

Expected responses:

- `https://awx.example.com/api/v2/ping/` -> `200`
- `https://hub.example.com/api/galaxy/` -> `403` before login
- `https://awx.example.com/pulp/api/v3/` -> Pulp API via gateway
- `https://awx.example.com/pulp/content/` -> Pulp content via gateway

## Gateway-Routed Hub Endpoints

Use the gateway for Pulp endpoints by default:

- `http://localhost:18088/pulp/api/v3/`
- `http://localhost:18088/pulp/content/`

Use the direct hub endpoint for Galaxy NG:

- `http://localhost:15001/api/galaxy/`
- `http://localhost:15001/auth/login/?next=/api/galaxy/`

## Operator Notes

- Keep direct host exposure minimal; prefer gateway-first access for shared interfaces.
- A `403` response from `/api/galaxy/` is a valid unauthenticated health signal for Hub.
- Keep this file in sync with `docker-compose.yml` and `.env.example` when changing ports.
