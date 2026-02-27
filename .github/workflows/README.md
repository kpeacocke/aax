# GitHub Actions CI/CD Integration

This document describes the CI/CD pipeline for the AAX project.

## Workflow Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                          DEVELOPMENT                             │
├─────────────────────────────────────────────────────────────────┤
│ feature/*, bugfix/*, hotfix/* branches                          │
│                                                                  │
│ Push → ci.yml:                                                   │
│   ├─ Lint Code (pre-commit)                                     │
│   ├─ Lint Dockerfiles (hadolint)                                │
│   ├─ Test Images (pytest image tests)                           │
│   └─ Security Scan (develop branch only)                        │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                        PULL REQUESTS                             │
├─────────────────────────────────────────────────────────────────┤
│ PR → main/develop                                                │
│                                                                  │
│ Runs: ci.yml + gitflow-enforce.yml                              │
│   ├─ Validates branch naming                                    │
│   ├─ Validates PR target branch                                 │
│   ├─ Lint Code                                                  │
│   ├─ Lint Dockerfiles                                           │
│   └─ Test Images                                                │
│                                                                  │
│ ✅ Must pass before merge allowed                                │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RELEASE (main branch)                       │
├─────────────────────────────────────────────────────────────────┤
│ Push to main → release.yml:                                      │
│   1. Pre-Release Tests                                           │
│      ├─ Lint Dockerfiles (fail-fast)                            │
│      ├─ Build all images                                        │
│      ├─ Run pytest test suite                                   │
│      └─ Run image smoke tests                                   │
│                                                                  │
│   2. Security Scan                                               │
│      ├─ Trivy scan (HIGH/CRITICAL only)                         │
│      ├─ Fail on vulnerabilities                                 │
│      └─ Upload to GitHub Security                               │
│                                                                  │
│   3. Create Release (release-please)                             │
│      ├─ Generate CHANGELOG                                       │
│      ├─ Create GitHub Release                                   │
│      └─ Tag with version                                        │
│                                                                  │
│   4. Build and Push (if release created)                         │
│      ├─ Build images with version tags                          │
│      ├─ Push to ghcr.io/kpeacocke/aax-*:VERSION                │
│      ├─ Push to ghcr.io/kpeacocke/aax-*:latest                 │
│      └─ Upload release artifacts                                │
└─────────────────────────────────────────────────────────────────┘
```

## Workflows

### 1. CI Pipeline ([ci.yml](.github/workflows/ci.yml))

**Triggers:**

- Push to: develop, feature/*, bugfix/*, hotfix/*, release/*
- Pull requests to: main, develop
- Only on changes to: images/, tests/, pyproject.toml

**Jobs:**

1. **Lint Code** - Pre-commit hooks (YAML, shell, etc.)
2. **Lint Dockerfiles** - Hadolint validation (fail on warning)
3. **Test Images** - Build + pytest image tests (matrix strategy)
4. **Security Scan** - Trivy scan (develop branch only, informational)

**Purpose:** Fast feedback during development and PR review

### 2. Gitflow Enforcement ([gitflow-enforce.yml](.github/workflows/gitflow-enforce.yml))

**Triggers:** All pull requests

**Validates:**

- Branch names follow convention: feature/*, bugfix/*, hotfix/*, release/*
- PR targets correct base: feature/bugfix→develop, hotfix/release→main

**Purpose:** Maintain clean git history and branching strategy

### 3. Release ([release.yml](.github/workflows/release.yml))

**Triggers:** Push to main branch

**Jobs (sequential):**

1. **Pre-Release Tests** (fail-fast: true)

- Lint all Dockerfiles
- Build all images
- Run full pytest test suite
- Run image smoke tests
- **Blocks release if any test fails**

1. **Security Scan** (fail-fast: false)

- Trivy scan for HIGH/CRITICAL vulnerabilities
- **Blocks release if vulnerabilities found**
- Uploads results to GitHub Security tab

1. **Create Release** (depends on: tests + security)

- Uses release-please for semantic versioning
- Generates CHANGELOG from conventional commits
- Creates GitHub Release with notes
- Tags version

1. **Build and Push** (only if release created)

- Builds images with version metadata
- Pushes to GitHub Container Registry:
  - `ghcr.io/kpeacocke/aax-IMAGE:VERSION`
  - `ghcr.io/kpeacocke/aax-IMAGE:latest`
- Generates release artifact manifest
- Uploads to release assets

**Purpose:** Automated, tested releases with semantic versioning

## No Duplication

The workflows are designed with clear separation:

| Workflow        | When                       | Tests  | Security       | Pushes Images              |
| --------------- | -------------------------- | ------ | -------------- | -------------------------- |
| **ci.yml**      | Development branches & PRs | ✅ Full | ℹ️ Develop only | ❌ No                       |
| **release.yml** | Main branch (release)      | ✅ Full | ✅ Blocking     | ✅ Yes (if release created) |

- **ci.yml** runs on feature branches and PRs for fast feedback
- **release.yml** runs only on main for production releases
- No workflow runs tests twice for the same commit
- Security scans are informational in dev, blocking in release

## Running Locally

Simulate CI pipeline locally:

```bash
# Lint Dockerfiles
hadolint images/*/Dockerfile

# Build all images
docker compose build

# Run full test suite
pytest tests/ -v

# Test specific image
pytest tests/test_images.py::TestEEBaseImage -v
```

## Adding New Images

When adding new images, update these locations:

### 1. Add to CI/Release Matrix

Both [ci.yml](.github/workflows/ci.yml) and [release.yml](.github/workflows/release.yml):

```yaml
strategy:
  matrix:
    image:
      - ee-base
      - your-new-image  # Add here
```

### 2. Add pytest Test Class

In [tests/test_images.py](../tests/test_images.py):

```python
class TestYourNewImage:
    """Tests for your-new-image."""
    IMAGE_NAME = "aax/your-new-image:latest"

    def test_image_builds(self):
        """Test that the image builds successfully."""
        result = subprocess.run(
          [
            "docker",
            "build",
            "-f",
            "images/your-new-image/Dockerfile",
            "-t",
            "aax/your-new-image:latest",
            "images/your-new-image",
          ],
          capture_output=True,
          text=True
        )
        assert result.returncode == 0

    # Add more tests...
```

### 3. Update Compose Build

Ensure the image builds via Compose:

```bash
docker compose build your-new-image
```

## GitHub Configuration

### Required Secrets

- `GITHUB_TOKEN` - Auto-provided by GitHub Actions (for GHCR push)

### Branch Protection Rules

Recommended settings for `main` and `develop`:

```yaml
main:
  required_status_checks:
    - "Lint Code"
    - "Lint Dockerfiles"
    - "Test Docker Images (ee-base)"
    - "check-branch-name"
    - "check-target-branch"
  require_pull_request_reviews: true
  require_linear_history: true

develop:
  required_status_checks:
    - "Lint Code"
    - "Lint Dockerfiles"
    - "Test Docker Images (ee-base)"
```

## Workflow Status Badges

Add to README.md:

```markdown
[![CI](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/ci.yml)
[![Release](https://github.com/kpeacocke/AAX/actions/workflows/release.yml/badge.svg)](https://github.com/kpeacocke/AAX/actions/workflows/release.yml)
```

## Troubleshooting

### Tests pass locally but fail in CI

- Check Python/Docker versions match
- Verify all dependencies installed
- Review full workflow logs
- Test with `pytest tests/ -v` locally

### Release not creating

- Check commit messages use conventional commits
- Verify tests pass on main branch
- Review release-please logs
- Ensure main branch is up to date

### Images not pushing to GHCR

- Verify `packages: write` permission set
- Check GHCR authentication
- Ensure image names are lowercase
- Review docker push logs

### Security scan blocking release

- Review Trivy output for vulnerabilities
- Update base images to patched versions
- If false positive, adjust Trivy config
- Consider severity threshold adjustment
