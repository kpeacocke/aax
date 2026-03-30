# Migration Notes

This document covers migration steps for the security-default changes introduced in AAX hardening.

## Summary of Breaking Changes

- Runtime secrets are required; weak defaults were removed.
- Images are pinned to explicit versions in compose, k8s, and CI.
- Published ports are localhost-first by default through HOST_BIND.
- AWX cookie security now uses explicit dev-only override:
  - AWX_ALLOW_INSECURE_COOKIES=false (default)

## .env Migration Snippets

Before:

```bash
AWX_SESSION_COOKIE_SECURE=true
AWX_CSRF_COOKIE_SECURE=true
```

After:

```bash
# Keep false for shared or production-like environments
AWX_ALLOW_INSECURE_COOKIES=false
```

Before:

```bash
VERSION=latest
AWX_IMAGE=aax/awx:latest
DEFAULT_EXECUTION_ENVIRONMENT=aax/ee-base:latest
```

After:

```bash
VERSION=1.0.0
AWX_IMAGE=aax/awx:1.0.0
DEFAULT_EXECUTION_ENVIRONMENT=aax/ee-base:1.0.0
```

## Kubernetes Migration Notes

- Ensure `aax-secrets` is populated with strong values before deploy.
- Rotate and replace any placeholder values used in old test/local manifests.
- AWX settings now interpret `AWX_ALLOW_INSECURE_COOKIES=true` as a local-dev-only override.

## Credential Rotation Checklist

- Rotate AWX admin password.
- Rotate PostgreSQL passwords (AWX, Hub, EDA).
- Rotate Django/secret keys (AWX, Galaxy, Pulp).
- Invalidate old API tokens after admin credential rotation.
- Re-run policy checks and secret scan after rotation.

## Validation Commands

```bash
pytest -q tests/test_repo_policy.py tests/test_docs_contract.py
pytest -q tests/test_compose.py -k "localhost or gateway or socket"
```
