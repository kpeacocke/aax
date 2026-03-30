# Production Secret Management

Use Kubernetes External Secrets (or equivalent) in production-like environments instead of committing static secret values.

## Recommended Path

- Use the production overlay at `k8s/overlays/production`.
- Deploy a compatible external-secrets controller.
- Configure your `ClusterSecretStore` and remote secret backend.
- Replace `change-me-secret-store` and key paths in `external-secret.example.yaml`.

## Why This Overlay Exists

- Base kustomization includes `k8s/secret.yaml` for local bootstrapping.
- Production overlay deletes that static Secret manifest and replaces it with `ExternalSecret`.

## Apply Example

```bash
kubectl apply -k k8s/overlays/production
```

## Validation

```bash
kubectl get externalsecret -n aax
kubectl get secret aax-secrets -n aax
```
