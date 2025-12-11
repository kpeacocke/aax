# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the AAX (Ansible Automation eXecution) platform to a Kubernetes cluster.

## Architecture

The deployment consists of:

- **Namespace**: `aax` - Isolated namespace for all resources
- **ConfigMap**: Shared environment configuration
- **PersistentVolumeClaims**: Storage for workspaces and build artifacts
- **Deployments**: Three main services (ee-base, ee-builder, dev-tools)
- **Services**: ClusterIP services for inter-pod communication

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl CLI tool configured
- Container images built and available:
  - `aax/ee-base:latest`
  - `aax/ee-builder:latest`
  - `aax/dev-tools:latest`
- Storage class `standard` available (or modify in `persistent-volumes.yaml`)

## Quick Start

### Deploy with kubectl

```bash
# Create namespace and resources
kubectl apply -f k8s/

# Check deployment status
kubectl get all -n aax

# View logs
kubectl logs -n aax -l app=ee-base
kubectl logs -n aax -l app=ee-builder
kubectl logs -n aax -l app=dev-tools
```

### Deploy with Kustomize

```bash
# Deploy using kustomize
kubectl apply -k k8s/

# View generated manifests without applying
kubectl kustomize k8s/
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
| workspace      | 10Gi | ReadWriteMany | Shared workspace for Ansible operations |
| ee-builds      | 20Gi | ReadWriteMany | Execution environment build outputs     |
| ee-definitions | 5Gi  | ReadWriteMany | EE definition files                     |
| dev-workspace  | 10Gi | ReadWriteMany | Development workspace                   |

### Deployments

#### ee-base

- **Image**: `aax/ee-base:latest`
- **Replicas**: 1
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Health Checks**: Python import tests
- **Security**: Non-root user (1000:1000)

#### ee-builder

- **Image**: `aax/ee-builder:latest`
- **Replicas**: 1
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Dependencies**: Waits for ee-base
- **Health Checks**: ansible-builder version
- **Volumes**: Docker socket (for building images)

#### dev-tools

- **Image**: `aax/dev-tools:latest`
- **Replicas**: 1
- **Resources**: 1-2 CPU, 1-2Gi memory
- **Dependencies**: Waits for ee-base
- **Health Checks**: ansible-navigator version
- **Environment**: PAGER="" for non-interactive use

## Accessing Services

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

All deployments enforce:

- Non-root user (UID 1000)
- No privilege escalation
- Dropped capabilities
- Security context constraints

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
