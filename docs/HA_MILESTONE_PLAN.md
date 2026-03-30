# HA Milestone Plan

This document defines practical HA milestones that map directly to repository artifacts and tests.

## Current implemented baseline

The repository now ships an optional HA overlay at `k8s/overlays/ha` that includes:

- Multi-replica Deployments for AWX web/task, Galaxy, Pulp API/content, EDA controller, and Gateway.
- PodDisruptionBudgets for key externally consumed control-plane services.
- Render/test coverage in `tests/test_kubernetes.py`.

Apply the optional overlay with:

```bash
kubectl apply -k k8s/overlays/ha
```

## Milestone 1: Control-plane replica resilience (implemented)

Scope:

- Increase stateless/control-plane service replicas.
- Add PodDisruptionBudgets for controlled voluntary disruption.

Exit criteria:

- `kubectl kustomize k8s/overlays/ha` succeeds.
- Tests verify replica counts and PDB presence.

## Milestone 2: Stateful dependency HA (planned)

Scope:

- Introduce PostgreSQL replication/failover design for AWX, Hub, and EDA data stores.
- Introduce Redis HA model for AWX/Hub/EDA cache and queue paths.

Exit criteria:

- Dependency failover playbook is documented.
- Failure-injection tests prove control-plane service continuity during dependency events.

## Milestone 3: Shared storage and failover validation (planned)

Scope:

- Validate shared content storage strategy for Pulp/Galaxy in replicated mode.
- Add replicated scenario resilience tests.

Exit criteria:

- Replicated scenarios are covered by automated tests.
- Recovery/failover runbook is documented and linked from docs index.
