# Event-Driven Ansible

AAX packages the upstream `quay.io/ansible/eda-server` runtime as
`aax-eda-controller`. The AAX entrypoint in `images/eda-server` runs upstream
API migrations and initial-data setup, and exposes the controller API on port
5000.

The maintained runtime is a set of roles using the same image:

| Kubernetes workload | Image argument | Purpose |
| ------------------- | -------------- | ------- |
| `eda-controller` | `api` | Controller API and one-time startup migration |
| `eda-worker` | `worker` | Background dispatch |
| `eda-activation-worker` | `activation-worker` | Rulebook activations |
| `eda-ws` | `ws` | WebSocket service |

Activation workers use the separate `aax-eda-podman` image through the
cluster-internal `eda-podman:8888` service. That workload is privileged to run
nested Podman and its container storage is persisted in `eda-podman-storage`.
The included NetworkPolicy restricts the Podman API to activation-worker pods
when the cluster network plugin enforces NetworkPolicy.

Kubernetes leaves the Podman service on the cluster's default pod DNS policy;
it does not set an `EDA_PODMAN_DNS` environment variable or assume a public
resolver. Verify external DNS from an activation-created container before
enabling real projects. If the cluster resolver cannot resolve required public
endpoints, configure `dnsConfig.nameservers` on the `eda-podman` Pod template
with a resolver approved and reachable in that cluster.

## Run with Compose

Configure the required EDA database password and controller secret key, then
start the EDA profile:

```bash
docker compose --profile eda up -d
docker compose --profile eda ps
curl http://localhost:15000/_healthz
```

The EDA API uses `EDA_SECRET_KEY` (falling back to `SECRET_KEY` in Compose),
`EDA_DB_PASSWORD`, and the `eda-postgres` / `eda-redis` services. Do not rotate
the secret key when reusing an existing EDA database.

## Kubernetes

The base and HA Kustomize configurations point at the published upstream-built
images. Before applying an update to an existing installation, back up the EDA
PostgreSQL database, `eda-projects`, and `eda-logs` PVC data. Keep the existing
PVCs; this migration does not rename or delete them.

The sample ConfigMap uses the same public AWX/EDA URLs as Compose. Change the
`EDA_CONTROLLER_URL`, `EDA_WEBSOCKET_BASE_URL`, `EDA_CSRF_TRUSTED_ORIGINS`, and
`EDA_ALLOWED_HOSTS` values in `k8s/configmap.yaml` to match the deployment's
public hostname before applying.

The production overlay deliberately removes the example Secret. Provision the
existing `aax-secrets` Secret out of band before applying that overlay; it must
contain the keys referenced by the manifests, including `SECRET_KEY`,
`EDA_DB_PASSWORD`, and the existing Hub/AWX credentials. The EDA runtime maps
`EDA_SECRET_KEY` to the existing `SECRET_KEY`, preserving the configured
credential.

See [Kubernetes deployment](../k8s/K8S.md) and
[upstream image builds](../scripts/build-bundle-image.sh).
