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

## Gateway-Routed Hub Endpoints

Use the gateway for Pulp endpoints by default:

- `http://localhost:18088/pulp/api/v3/`
- `http://localhost:18088/pulp/content/`

## Operator Notes

- Keep direct host exposure minimal; prefer gateway-first access for shared interfaces.
- Keep this file in sync with `docker-compose.yml` and `.env.example` when changing ports.
