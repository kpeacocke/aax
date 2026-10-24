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
- Secret scanning and remediable HIGH/CRITICAL vulnerabilities are release gates.

## Mandatory CI Baseline Gates

- `tests/test_repo_policy.py`
- `tests/test_docs_contract.py`
- `tests/test_bundle_publication.py`
- Secret scanning workflow checks
- Image vulnerability scanning in CI/release workflows. All findings are retained
  in GitHub Security; required PR checks retain their fixable CRITICAL threshold
  so existing HIGH findings do not prevent remediation PRs. Publication blocks
  HIGH/CRITICAL findings with a scanner-reported fix.
  Main-channel multi-architecture candidates are scanned by
  digest before deployment tags are promoted. Candidate tags are not deployment tags.

## Upstream Blockers

A clean package resolver does not establish a clean image. In particular, pip
vendors its own copies of libraries: constraints on installed `urllib3`, `msgpack`,
or `setuptools` do not replace pip's vendored code. If a scanner reports fixes for
those libraries but current pip has not incorporated them, publication remains
blocked. Do not delete vulnerability metadata, patch vendored code ad hoc, or add
blanket ignores to turn the gate green.

Distribution findings without patched vendor packages remain visible. A passing
fixable-vulnerability gate does not certify that the image has no known issues,
nor does it replace full-stack runtime tests. Review the exact bundle reports
and deployed image digests before production use.

## Operator Checklist

- Set all required secrets before startup.
- Confirm localhost-first bind policy.
- Confirm gateway-first exposure model for shared endpoints.
- Verify policy checks before merge or release.
