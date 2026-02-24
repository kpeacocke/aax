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

### Using Make

```bash
# Run all tests (when implemented in Makefile)
make test
```

## Test Structure

- `test_images.py` - Tests for all Docker images
  - `TestEEBaseImage` - Tests for the Ansible EE base image
  - Additional test classes for other images can be added here

## Writing New Tests

When adding new images, create new test classes following this pattern:

```python
class TestNewImage:
    """Tests for the new image."""

    IMAGE_NAME = "aax/new-image:latest"

    def test_image_builds(self):
        """Test that the image builds successfully."""
        result = subprocess.run(
            ["make", "build-new-image"],
            capture_output=True,
            text=True,
            cwd="/workspaces/AAX"
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

    # Add more tests...
```

## Test Requirements

- pytest >= 7.0
- Docker (for running container tests)
- Make (for build commands)

## CI/CD Integration

These tests can be integrated into GitHub Actions or other CI/CD pipelines:

```yaml
- name: Run Docker Image Tests
  run: |
    pytest tests/ -v
```
