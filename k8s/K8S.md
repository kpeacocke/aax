# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the AAX (Ansible Automation eXecution) platform to a Kubernetes cluster.

## Architecture

The deployment consists of:

- **Namespace**: `aax` - Isolated namespace for all resources
- **ConfigMap**: Shared environment configuration
- **PersistentVolumeClaims**: Existing AWX, Hub, and EDA data claims plus workspace/build storage
- **Deployments**: AWX, Hub/Pulp, EDA, gateway, and development-tool workloads
- **Services**: ClusterIP services for inter-pod communication, including EDA API, WebSocket, and private Podman endpoints

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl CLI tool configured
- Development-tool images built and available:
  - `aax/ee-base:1.0.0`
  - `aax/ee-builder:1.0.0`
  - `aax/dev-tools:1.0.0`
- Storage class `hostpath` available (or update `persistent-volumes.yaml` for the cluster)
- Registry access to the pinned AAX bundle images in the Kustomize image map

## Quick Start

### Deploy with kubectl

```bash
# Apply the Kustomize base so image names and tags are transformed
kubectl apply -k k8s/

# Check deployment status
kubectl get all -n aax

# View logs
kubectl logs -n aax -l app=ee-base
kubectl logs -n aax -l app=ee-builder
kubectl logs -n aax -l app=dev-tools
kubectl logs -n aax -l app=eda-controller
```

### Deploy with Kustomize

```bash
# Deploy using kustomize
kubectl apply -k k8s/

# View generated manifests without applying
kubectl kustomize k8s/
```

### Maintained Hub and EDA images

The manifests use the published `ghcr.io/kpeacocke/aax-*` image names after
Kustomize applies the image map. `aax-pulp`, `aax-galaxy-ng`,
`aax-eda-controller`, and `aax-eda-podman` are built from the upstream sources
and runtime wrappers documented by `scripts/build-bundle-image.sh`; the legacy
`images/pulp`, `images/galaxy-ng`, and `images/eda-controller` build paths have
been retired. The base, HA, and production overlays pin each image to a verified
registry digest. The `aax-pulp` reference is the published compatibility alias
for the same maintained Galaxy image digest; the bundle publisher derives it
from the `galaxy-ng` candidate.

The Hub roles use the upstream entrypoint commands (`run api`, `run
content-app`, `run worker`). The Pulp encryption-key path points into the
existing `hub-pulp-storage` claim so it reuses `/var/lib/pulp/db-encryption.key`
instead of generating a new key and losing access to encrypted database fields.
The existing Hub, EDA, and AWX PVC names are intentionally unchanged. Back up
the application databases and persistent volumes before applying image or
schema upgrades; do not prune the namespace as part of this migration.
The existing `hub-assets` claim is retained for rollback/data preservation, but
the maintained Hub image serves its baked-in static assets and the workloads
must not mount that claim over `/app/static`.

The EDA stack runs API, background-worker, activation-worker, and WebSocket
roles from the maintained EDA image. Activations use a separate privileged
Podman service with persisted container storage. See [EDA runtime guidance](../docs/EDA.md)
for the required network and public-URL settings.

### Production credentials

The production overlay removes the sample `aax-secrets` Secret. Provision that
Secret out of band before applying the overlay, retaining the existing
`SECRET_KEY`, Hub database/Pulp credentials, AWX, and EDA database credentials.
The EDA runtime maps `EDA_SECRET_KEY` to `SECRET_KEY`. No external-secret
provider is assumed by these manifests.

The maintained Hub entrypoint does not create an administrator from an
environment variable. Create the initial Hub administrator interactively using
the upstream Django command after the API pod is ready:

```bash
kubectl exec -n aax -it deploy/pulp-api -- django-admin createsuperuser
```

Do not pass the password on the command line or store it in the Kubernetes
Secret.

```bash
kubectl kustomize --load-restrictor LoadRestrictionsNone k8s/overlays/production/ \
  | kubectl apply -f -
```

## Resource Overview

### Namespace

```yaml
Namespace: aax
```

All resources are deployed in the `aax` namespace for isolation.

### ConfigMap

```yaml
Name: aax-config
Data:
  - ANSIBLE_NOCOWS=1
  - PYTHONUNBUFFERED=1
  - PIP_NO_CACHE_DIR=1
  - PIP_ROOT_USER_ACTION=ignore
```

### Persistent Storage

| PVC            | Size | Access Mode   | Purpose                                 |
| -------------- | ---- | ------------- | --------------------------------------- |
| workspace      | 10Gi | ReadWriteOnce | Shared workspace for Ansible operations |
| ee-builds      | 20Gi | ReadWriteOnce | Execution environment build outputs     |
| ee-definitions | 5Gi  | ReadWriteOnce | EE definition files                     |
| dev-workspace  | 10Gi | ReadWriteOnce | Development workspace                   |
| hub-pulp-storage | 20Gi | ReadWriteOnce | Pulp content and existing encryption key |
| hub-assets | 5Gi | ReadWriteOnce | Retained legacy Hub assets; not mounted by maintained workloads |
| eda-postgres-data | 10Gi | ReadWriteOnce | EDA database |
| eda-projects | 10Gi | ReadWriteOnce | EDA projects |
| eda-logs | 5Gi | ReadWriteOnce | EDA logs |
| eda-podman-storage | 20Gi | ReadWriteOnce | EDA activation container storage |

The HA overlay schedules multiple replicas that share Hub and EDA data. Use a
storage class and access mode that support the desired cross-node topology;
do not change an already-bound claim's name or delete it to alter storage
access. For multi-node HA, provision appropriate shared storage before
enabling the overlay.

### Deployments

#### ee-base

- **Image**: `aax/ee-base:1.0.0`
- **Replicas**: 1
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Health Checks**: Python import tests
- **Security**: Non-root user (1000:1000)

#### ee-builder

- **Image**: `aax/ee-builder:1.0.0`
- **Replicas**: 1
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Dependencies**: Waits for ee-base
- **Health Checks**: ansible-builder version
- **Volumes**: Docker socket (for building images)

#### dev-tools

- **Image**: `aax/dev-tools:1.0.0`
- **Replicas**: 1
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Dependencies**: Waits for ee-base
- **Health Checks**: ansible-navigator version
- **Environment**: PAGER="" for non-interactive use

## Accessing Services

## AWX Web Pattern (Compose + Kubernetes)

AWX web traffic requires an nginx vhost that proxies Django requests to uWSGI (`127.0.0.1:8050`) and websocket traffic to daphne (`127.0.0.1:8051`).

- In Compose, this is mounted from `images/awx/nginx-awx.conf` to `/etc/nginx/conf.d/awx.conf`.
- In Compose, this is generated in the `awx-web` entrypoint and written to `/etc/nginx/conf.d/awx.conf` at container start.
- In Kubernetes, the same vhost content is delivered via ConfigMap `awx-nginx` in `awx-nginx-configmap.yaml` and mounted at `/etc/nginx/conf.d/awx.conf` in `awx-web`.

This keeps AWX behavior consistent across both deployment targets and avoids falling back to the default nginx static-file server.

### Exec into containers

```bash
# Access ee-base
kubectl exec -it -n aax deployment/ee-base -- /bin/bash

# Access ee-builder
kubectl exec -it -n aax deployment/ee-builder -- /bin/bash

# Access dev-tools
kubectl exec -it -n aax deployment/dev-tools -- /bin/bash
```

### Run Ansible commands

```bash
# Run ansible from ee-base
kubectl exec -n aax deployment/ee-base -- ansible --version

# Build execution environment
kubectl exec -n aax deployment/ee-builder -- ansible-builder --help

# Use ansible-navigator
kubectl exec -n aax deployment/dev-tools -- ansible-navigator --version

# Run ansible-lint
kubectl exec -n aax deployment/dev-tools -- ansible-lint --version
```

## Scaling

Scale deployments as needed:

```bash
# Scale dev-tools to 3 replicas
kubectl scale -n aax deployment/dev-tools --replicas=3

# Scale all deployments
kubectl scale -n aax deployment --all --replicas=2
```

## Resource Management

### CPU and Memory Limits

Each deployment has defined resource requests and limits:

```yaml
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
  limits:
    cpu: "2"
    memory: "2Gi"
```

Adjust these values in the deployment files based on your workload requirements.

### Storage Classes

The default storage class is `standard`. To use a different storage class:

1. Edit `persistent-volumes.yaml`
2. Change `storageClassName: standard` to your desired class
3. Reapply: `kubectl apply -f k8s/persistent-volumes.yaml`

## Monitoring

### Check pod status

```bash
# Get all resources
kubectl get all -n aax

# Get pod details
kubectl describe pod -n aax -l app=ee-base

# Check events
kubectl get events -n aax --sort-by='.lastTimestamp'
```

### View logs

```bash
# Tail logs
kubectl logs -n aax -f deployment/ee-base
kubectl logs -n aax -f deployment/ee-builder
kubectl logs -n aax -f deployment/dev-tools

# View previous container logs
kubectl logs -n aax -p deployment/dev-tools
```

### Health checks

```bash
# Check readiness
kubectl get pods -n aax -o wide

# Describe pod to see health check results
kubectl describe pod -n aax <pod-name>
```

## Security

### Pod Security

Application containers run as configured by their maintained images. The
`eda-podman` workload is intentionally privileged for nested Podman; keep it
internal to the cluster and use a CNI that enforces the included NetworkPolicy.

### Docker Socket Mounting (ee-builder)

⚠️ **Security Consideration**: The `ee-builder` deployment mounts the Docker daemon socket at `/var/run/docker.sock` to enable container image building within the pod. This is a privileged operation that grants container-level access to the Docker daemon.

**Risks**:

- Container escape vulnerabilities could lead to host compromise
- Allows arbitrary Docker operations (not just image building)
- Circumvents normal container isolation

**Mitigation strategies**:

1. **Restrict to trusted networks**: Use NetworkPolicies to limit access to ee-builder
2. **Monitor socket usage**: Audit Docker API calls
3. **Use container registries**: Push prebuilt images instead of building in-cluster
4. **Rootless Docker**: Consider rootless Docker daemon for additional isolation
5. **Pod Security Standards**: Run only trusted code in ee-builder

**For production environments**, consider:

- Using a dedicated image builder outside the cluster
- Implementing Kaniko or BuildKit for rootless builds
- Running ee-builder in a separate, isolated cluster

### Network Policies

To add network policies for isolation:

```bash
# Example: Restrict ingress to dev-tools
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dev-tools-policy
  namespace: aax
spec:
  podSelector:
    matchLabels:
      app: dev-tools
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/part-of: aax
EOF
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl get pods -n aax

# Describe pod for events
kubectl describe pod -n aax <pod-name>

# Check logs
kubectl logs -n aax <pod-name>
```

### Storage issues

```bash
# Check PVC status
kubectl get pvc -n aax

# Describe PVC
kubectl describe pvc -n aax workspace

# Check if storage class exists
kubectl get storageclass
```

### Image pull errors

```bash
# Verify images exist locally or in registry
docker images | grep aax

# If using private registry, create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n aax

# Add imagePullSecrets to deployment
kubectl patch deployment -n aax ee-base \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"regcred"}]}}}}'
```

### Health check failures

```bash
# Check if commands exist in container
kubectl exec -n aax deployment/ee-base -- which ansible
kubectl exec -n aax deployment/dev-tools -- which ansible-navigator

# Test health check command manually
kubectl exec -n aax deployment/ee-base -- python3 -c "import ansible; import ansible_runner"
```

## Cleanup

Remove all resources:

```bash
# Delete all resources in namespace
kubectl delete namespace aax

# Or delete individual resources
kubectl delete -f k8s/
```

## Production Considerations

### High Availability

For production deployments:

1. **Increase replicas**:

   ```bash
   kubectl scale -n aax deployment --all --replicas=3
   ```

2. **Add pod anti-affinity** to spread pods across nodes
3. **Use StatefulSets** if persistent identity is needed
4. **Configure pod disruption budgets**:

   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: ee-base-pdb
     namespace: aax
   spec:
     minAvailable: 1
     selector:
       matchLabels:
         app: ee-base
   ```

### Production Storage Considerations

- Use **ReadWriteMany** storage for shared volumes
- Consider **NFS**, **CephFS**, or cloud provider storage
- Enable **volume snapshots** for backups
- Set appropriate **storage class** with retention policies

### Monitoring and Observability

Integrate with monitoring stack:

```yaml
# Add Prometheus annotations
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

### Resource Quotas

Set namespace quotas:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: aax-quota
  namespace: aax
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
```

## Next Steps

- Configure ingress for external access
- Set up CI/CD for automated deployments
- Implement GitOps with ArgoCD or Flux
- Add Helm charts for easier management
- Configure backup and disaster recovery
- Implement monitoring and alerting
- Set up log aggregation
