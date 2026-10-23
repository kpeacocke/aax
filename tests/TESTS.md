# AAX Docker Image Tests

This directory contains automated tests for the AAX Docker images using pytest.

## Running Tests

### Using VS Code Test Explorer

1. Open the Testing view (beaker icon in the sidebar or `Cmd+Shift+T`)
2. Tests will be automatically discovered
3. Click ▶️ next to any test to run it
4. Click 🐞 to debug a test

### Using Command Line

```bash
# Run canonical policy, publication-security and Hub-bootstrap tests (no Docker)
make test

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_images.py

# Run specific test class
pytest tests/test_images.py::TestEEBaseImage

# Run specific test
pytest tests/test_images.py::TestEEBaseImage::test_ansible_installed

# Run with verbose output
pytest -v tests/

# Run with coverage (if installed)
pytest --cov=tests/ tests/
```

## Test Structure

- `test_images.py` - Tests for all Docker images
  - `TestEEBaseImage` - Tests for the Ansible EE base image
  - Additional test classes for other images can be added here
- `test_bundle_publication.py` - Executes publication scripts with a fake registry
  client and checks unique run tags, fail-closed vulnerability thresholds, and
  digest-scoped promotion, exact-image supplemental OS coverage, runtime patch
  ordering, RPM upgrade selection/postconditions and the Java database fallback.
  Requires `jq`, `bash`, and PyYAML; no registry writes.
- `test_hub_bootstrap.py` - Validates durable encryption-key creation, concurrent
  initialization, malformed-key failure and consistent shared Hub storage settings.

Source-build regressions also run inside their respective Docker builders.
`images/rpm-security/setuptools_regression.py` must run from the unpacked
setuptools source, with that source on `PYTHONPATH` and Python 3.12. It tests both
Unicode normalization forms, all exclusion directives and actual source archive
contents; it is not a test of whichever setuptools happens to be installed on
the host.

The EDA source build runs `images/runtime-security/test_eda_crypto.py` against
the installed wheel. It checks AES-256 round trips, legacy ciphertext, tampering,
expiry and invalid keys after upgrading cryptography; no database values or
encryption keys are replaced.

## Writing New Tests

When adding new images, create new test classes following this pattern:

```python
class TestNewImage:
    """Tests for the new image."""

    IMAGE_NAME = "aax/new-image:1.0.0"

    def test_image_builds(self):
        """Test that the image builds successfully."""
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                "images/new-image/Dockerfile",
                "-t",
                "aax/new-image:1.0.0",
                "images/new-image",
            ],
            capture_output=True,
            text=True,
            cwd="/workspaces/aax"
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    # Add more tests...
```

## Test Requirements

- pytest >= 7.0
- Docker (for running container tests)
- Docker Compose 5.1.0 or later

## CI/CD Integration

These tests can be integrated into GitHub Actions or other CI/CD pipelines:

```yaml
- name: Run Docker Image Tests
  run: |
    pytest tests/ -v
```
