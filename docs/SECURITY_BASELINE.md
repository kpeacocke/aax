# Security Baseline

This document defines baseline controls for local-dev and production-like AAX operation.

## Profiles

### Local-Dev Baseline

- `HOST_BIND` may be set to `127.0.0.1` (default) or explicitly opened for isolated lab testing.
- `AWX_ALLOW_INSECURE_COOKIES` may be set to `true` only for local HTTP lab flows.
- Placeholder secret values are allowed only for non-shared disposable environments.
- Security scans are expected to run, but findings may be triaged as non-blocking during early iteration.

### Production-Like Baseline

- `HOST_BIND` remains localhost by default unless access requirements are explicitly approved.
- `AWX_ALLOW_INSECURE_COOKIES` must remain `false`.
- Required secrets must be strong operator-provided values.
- No weak fallback passwords or secret defaults in runtime config.
- Policy checks must pass (repo policy + docs contract tests).
- Secret scanning and vulnerability scanning are treated as release gates.

## Mandatory CI Baseline Gates

- `tests/test_repo_policy.py`
- `tests/test_docs_contract.py`
- Secret scanning workflow checks
- Image vulnerability scanning in CI/release workflows

## Operator Checklist

- Set all required secrets before startup.
- Confirm localhost-first bind policy.
- Confirm gateway-first exposure model for shared endpoints.
- Verify policy checks before merge or release.
