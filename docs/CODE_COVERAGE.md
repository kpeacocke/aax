# Code Coverage Guide

Guide for running tests with code coverage analysis in AAX.

## Overview

Code coverage measures how much of your codebase is exercised by automated tests. AAX is configured to collect comprehensive coverage metrics across Python tests.

### Coverage Metrics

- **Line Coverage**: Percentage of lines executed by tests
- **Branch Coverage**: Percentage of code branches (if/else paths) covered
- **Missing Lines**: Identifies untested code paths
- **Coverage Reports**: HTML, terminal, and XML formats

## Running Tests with Coverage

### Basic coverage report (terminal)

```bash
# Run all tests with coverage
pytest --cov

# Run specific test file with coverage
pytest tests/test_images.py --cov

# Run specific test with coverage
pytest tests/test_images.py::TestEEBaseImage::test_ee_base_ansible_installed --cov
```

### Generate HTML coverage report

```bash
# HTML report already enabled in pyproject.toml
pytest --cov

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Show missing lines

```bash
# Terminal report shows lines not covered
pytest --cov --cov-report=term-missing
```

### Generate XML report (CI/CD)

```bash
# XML format for CI integration (Codecov, etc.)
pytest --cov --cov-report=xml

# View generated file
cat coverage.xml
```

### Coverage with branch tracking

```bash
# Measure branch coverage (if/else paths)
pytest --cov --cov-branch

# Combined report
pytest --cov --cov-report=html --cov-report=term-missing --cov-branch
```

## Coverage Configuration

### Key settings in pyproject.toml

```toml
[tool.coverage.run]
branch = true                    # Track branches (if/else)
source = ["tests", "images"]    # What to measure
omit = [                         # Exclude patterns
    "*/tests/*",
    "*/site-packages/*"
]

[tool.coverage.report]
precision = 2                     # Decimal places
show_missing = true              # Show uncovered lines
exclude_lines = [                # Ignore patterns
    "pragma: no cover",
    "raise NotImplementedError",
    "if __name__ == .__main__.:"
]
```

### Excluding code from coverage

Mark code that shouldn't be covered:

```python
def debug_function():  # pragma: no cover
    """This code is not critical and can be excluded."""
    pass

if __name__ == "__main__":  # pragma: no cover
    # CLI code not tested
    pass
```

## Viewing Coverage Reports

### Terminal Report

```bash
pytest --cov --cov-report=term-missing:skip-covered

# Output example:
# tests/test_images.py 85% (17/20)  - 2 missing
# tests/test_compose.py 92% (23/25)  - 1 missing
# tests/test_kubernetes.py 78% (18/23) - 5 missing
# ===== 85% coverage =====
```

### HTML Report Structure

```text
htmlcov/
├── index.html          # Coverage summary
├── status.json         # Machine-readable results
└── <file>_py.html      # Per-file coverage details
```

Navigate with:

- **Index page**: Overall statistics and file list
- **File pages**: Color-coded line coverage
  - Green: Executed
  - Red: Not executed
  - Yellow: Partial (branch coverage)

### Coverage Report Details

In the HTML report, each line shows:

```python
17  │ def install_packages():     # GREEN - executed
18  │     if not packages:        # YELLOW - executed but branches not all tested
19  │         return              # RED - not executed
20  │     for pkg in packages:    # GREEN - executed
21  │         run_install(pkg)   # GREEN - executed
```

## Setting Coverage Targets

### Require minimum coverage

```bash
# Fail if coverage drops below 80%
pytest --cov --cov-fail-under=80

# Specific file minimum
pytest --cov --cov-fail-under=85 --cov-report=term-missing
```

### Pre-commit hook for coverage

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-coverage
        name: pytest-coverage
        entry: pytest --cov --cov-fail-under=80
        language: system
        stages: [commit]
        types: [python]
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests with Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r .devcontainer/requirements.txt
          pip install docker

      - name: Run tests with coverage
        run: pytest --cov --cov-report=xml --cov-report=term-missing

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
```

### GitLab CI

```yaml
test:coverage:
  image: python:3.11
  script:
    - pip install -r .devcontainer/requirements.txt
    - pip install docker
    - pytest --cov --cov-report=xml --cov-report=term-missing
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Jenkins

```groovy
stage('Test & Coverage') {
    steps {
        sh 'pip install -r .devcontainer/requirements.txt'
        sh 'pytest --cov --cov-report=xml --cov-report=html'
        publishHTML([
            reportDir: 'htmlcov',
            reportFiles: 'index.html',
            reportName: 'Coverage Report'
        ])
        step([$class: 'CoberturaPublisher',
              autoUpdateHealth: false,
              autoUpdateStability: false,
              coberturaReportFile: 'coverage.xml'])
    }
}
```

## Coverage Badge in README

Add coverage badge to README:

### Codecov

```markdown
[![codecov](https://codecov.io/gh/kpeacocke/AAX/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/kpeacocke/AAX)
```

### Custom badge (from CI)

```markdown
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)
```

### Update dynamically

```bash
# In CI/CD pipeline:
COVERAGE=$(pytest --cov --cov-report=term-missing 2>&1 | grep TOTAL | awk '{print $NF}' | sed 's/%//')
echo "Coverage: $COVERAGE%"
```

## Improving Coverage

### Find uncovered code

```bash
# Run with terminal report
pytest --cov --cov-report=term-missing:skip-covered

# Identifies files with low coverage:
# tests/test_images.py 64% - Lines 42, 48, 55 missing
```

### Write tests for missing coverage

```python
# Original code (25% coverage)
def validate_config(config):
    if not config:
        return False
    if 'name' not in config:
        return False
    return True

# Add test cases for all paths
def test_validate_config_empty():
    assert validate_config({}) == False

def test_validate_config_no_name():
    assert validate_config({'version': 1}) == False

def test_validate_config_valid():
    assert validate_config({'name': 'test', 'version': 1}) == True
```

### Coverage-driven development

```bash
# 1. Write test that documents desired behavior
def test_new_feature():
    result = new_feature(input_data)
    assert result == expected_output

# 2. Run coverage to see as uncovered
pytest --cov

# 3. Implement feature
def new_feature(data):
    # Implementation here
    pass

# 4. Verify coverage improves
pytest --cov
```

## Best Practices

### Coverage as a guide, not a goal

⚠️ **High coverage ≠ High quality**

```python
# 100% coverage but bad tests:
def test_function_exists():
    assert function_with_complex_logic is not None

# Better test:
def test_function_returns_correct_value():
    assert function_with_complex_logic(test_input) == expected_output

def test_function_handles_edge_cases():
    assert function_with_complex_logic(None) == default_value
    assert function_with_complex_logic([]) == empty_result
```

### Test multiple scenarios

```python
# Test happy path
def test_success_case():
    result = process_data(valid_input)
    assert result.success == True

# Test error handling
def test_invalid_input():
    result = process_data(invalid_input)
    assert result.success == False

# Test edge cases
def test_empty_input():
    result = process_data([])
    assert result.empty == True
```

### Use coverage to identify risky code

High coverage doesn't guarantee correctness. Focus on:

- **Critical paths**: User-facing features, security code
- **Error handling**: Exception handlers, validation
- **Edge cases**: Boundary conditions, empty inputs
- **Integration points**: Database, API calls, external services

## Performance Impact

### Coverage overhead

Coverage collection adds slight overhead:

```bash
# Without coverage (baseline)
pytest tests/
# ~5 seconds

# With coverage (with overhead)
pytest --cov tests/
# ~7-8 seconds (20-60% slower)

# Useful for CI but OK for dev
```

### Selective coverage

Only measure what you need:

```bash
# Measure specific modules
pytest --cov=images --cov=tests

# Exclude heavy modules
pytest --cov --cov-config=.coveragerc
```

## Troubleshooting

### Coverage missing imports

```bash
# If coverage can't import modules:
pytest --cov --cov-report=term-missing -v

# Check PYTHONPATH
export PYTHONPATH=/workspaces/aax:$PYTHONPATH
pytest --cov
```

### Pytest-cov not found

```bash
# Install coverage tools
pip install pytest-cov

# Or from requirements
pip install -r .devcontainer/requirements.txt
```

### XML report not generated

```bash
# Ensure output file is writable
ls -la coverage.xml

# Check pytest output
pytest --cov --cov-report=xml -v

# Verify file exists
cat coverage.xml | head -20
```

## Configuration Files

### Basic coverage (.coveragerc)

```ini
[run]
branch = True
source = .
omit =
    */tests/*
    */site-packages/*
    setup.py

[report]
precision = 2
show_missing = True
skip_covered = False
```

### Advanced configuration (pyproject.toml)

```toml
[tool.coverage.run]
branch = true
parallel = true
source = ["src", "tests"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:"
]

[tool.coverage.html]
directory = "htmlcov"
```

## See Also

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing Guide](tests/README.md)
- [Contributing Guide](../CONTRIBUTING.md)
