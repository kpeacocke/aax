# CI/CD Workflow Decision Tree

Use this guide to understand which workflow runs when and why.

## When I push code

```text
START: git push
    ↓
    ├─ Branch = main
    │   └─→ release.yml runs
    │       ├─ All tests (blocking)
    │       ├─ Security scan (blocking)
    │       ├─ Create release (if tests pass)
    │       └─ Push images to GHCR (if release created)
    │
    ├─ Branch = develop
    │   └─→ ci.yml runs
    │       ├─ Lint code
    │       ├─ Lint Dockerfiles
    │       ├─ Test images
    │       └─ Security scan (informational)
    │
    └─ Branch = feature/*, bugfix/*, hotfix/*
        └─→ ci.yml runs
            ├─ Lint code
            ├─ Lint Dockerfiles
            └─ Test images
```

## When I open a PR

```text
START: Create PR
    ↓
    ├─→ gitflow-enforce.yml runs
    │   ├─ Check branch name
    │   └─ Check PR target
    │
    └─→ ci.yml runs
        ├─ Lint code
        ├─ Lint Dockerfiles
        └─ Test images

Must all pass ✅ before merge allowed
```

## What tests run where?

| Test Type            | Feature Branch | Develop Branch | PR to Main | Main Branch (Release)       |
| -------------------- | -------------- | -------------- | ---------- | --------------------------- |
| **Pre-commit hooks** | ✅ ci.yml       | ✅ ci.yml       | ✅ ci.yml   | ❌ Not needed                |
| **Hadolint**         | ✅ ci.yml       | ✅ ci.yml       | ✅ ci.yml   | ✅ release.yml (blocking)    |
| **Pytest suite**     | ✅ ci.yml       | ✅ ci.yml       | ✅ ci.yml   | ✅ release.yml (blocking)    |
| **Make tests**       | ✅ ci.yml       | ✅ ci.yml       | ✅ ci.yml   | ✅ release.yml (blocking)    |
| **Security scan**    | ❌              | ℹ️ ci.yml       | ❌          | ✅ release.yml (blocking)    |
| **Push images**      | ❌              | ❌              | ❌          | ✅ release.yml (if released) |

## Decision: Should I run tests?

```text
Are you working on:
    ├─ New feature/bugfix?
    │   └─→ Tests run automatically on push (ci.yml)
    │       Run locally first: make test-ee-base
    │
    ├─ PR review?
    │   └─→ Tests run automatically (ci.yml + enforce)
    │       Check Actions tab for results
    │
    └─ Ready to release?
        └─→ Tests run automatically on merge to main (release.yml)
            All tests must pass before release created
```

## Key Principles

### 1. **No Duplication**

- CI tests development work
- Release tests production releases
- Same test, different purpose

### 2. **Fail Fast**

- Linting before building
- Tests before security scans
- Security before release creation
- Release before image push

### 3. **Appropriate Strictness**

- Development: Fast feedback, informational security
- Release: Blocking tests, blocking security, no exceptions

### 4. **Clear Ownership**

- `ci.yml`: Development quality gate
- `release.yml`: Production release gate
- `gitflow-enforce.yml`: Process compliance
- No overlap in responsibilities
