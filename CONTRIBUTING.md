# Contributing to AAX

Thank you for your interest in contributing to AAX! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (configuration files, commands, etc.)
- **Describe the behaviour you observed** and what you expected
- **Include logs and screenshots** if applicable
- **Specify your environment:**
  - OS (macOS, Windows, Linux distribution)
  - Docker version
  - Docker Compose version
  - AAX version/commit hash

**Bug Report Template:**

```markdown
**Description:**
A clear description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behaviour:**
What you expected to happen

**Actual Behaviour:**
What actually happened

**Environment:**
- OS: [e.g., macOS 13.0, Ubuntu 22.04]
- Docker: [e.g., 24.0.5]
- Docker Compose: [e.g., 5.1.0]
- AAX Version: [e.g., v1.0.0, commit abc123]

**Logs:**

```text
Paste relevant logs here
```

**Additional Context:**
Any other context about the problem

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the proposed enhancement
- **Explain why this enhancement would be useful** to most users
- **List any alternatives** you've considered
- **Include mockups or examples** if applicable

### Pull Requests

We actively welcome your pull requests:

1. **Fork the repository** and create your branch from `develop` (or `main` for hotfixes)
2. **Follow the gitflow branching strategy** (see below)
3. **Make your changes** following our coding standards
4. **Ensure Docker Compose configuration is valid**
5. **Update documentation** as needed
6. **Write conventional commit messages** (see below)
7. **Submit a pull request** to the correct target branch

## Development Setup

### Prerequisites

- Docker Desktop (macOS/Windows) or Docker Engine + Docker Compose 5.1.0 (Linux)
- Git

### Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/AAX.git
cd AAX

# Add upstream remote
git remote add upstream https://github.com/kpeacocke/AAX.git

# Create a branch for your changes
git checkout -b feature/my-feature

# Install pre-commit hooks
pre-commit install

# Copy example environment file
cp .env.example .env

# Start development environment
docker compose up -d
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_images.py -v

# Run linters
pre-commit run --all-files

# Or manually
flake8 .
black --check .
pylint src/
yamllint .
```

### Building Images

```bash
# Build all images
docker compose build

# Build specific service (controller stack)
docker compose --profile controller build awx-web

# Build without cache
docker compose build --no-cache
```

## Coding Standards

### Shell Scripts

- Use `#!/bin/bash` or `#!/bin/sh` shebang
- Use `set -euo pipefail` for bash scripts
- Quote variables: `"${var}"`
- Use shellcheck for validation

### YAML

- Use 2 spaces for indentation
- Use `yamllint` for validation
- Keep lines under 120 characters when possible

### Docker

- Use multi-stage builds when appropriate
- Minimize layers
- Use `.dockerignore` files
- Avoid running as root when possible
- Pin base image versions

### Documentation

- Use Markdown for documentation
- Keep line length to 120 characters
- Include code examples where helpful
- Update README.md for user-facing changes

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Adding or updating tests
- `build:` Build system changes
- `ci:` CI/CD changes
- `chore:` Other changes that don't modify src or test files

### Examples

```text
feat(awx): add support for custom execution environments

fix(postgres): resolve connection pool exhaustion issue

docs: update installation instructions for Windows

ci: add automated security scanning workflow
```

### Commit Message Best Practices

- Use the imperative mood ("add feature" not "added feature")
- Capitalize the first letter of the description
- Don't end the description with a period
- Keep the first line under 72 characters
- Separate subject from body with a blank line
- Use the body to explain what and why vs. how
- Reference issues and pull requests in the footer

## Branch Naming

Use descriptive branch names with prefixes:

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test updates
- `chore/` - Maintenance tasks

**Examples:**

- `feature/add-ldap-authentication`
- `fix/receptor-connection-timeout`
- `docs/update-backup-procedures`

## Pull Request Process

1. **Update Documentation** - Ensure README and relevant docs are updated
2. **Update CHANGELOG** - Add entry describing your changes
3. **Test Thoroughly** - Ensure all tests pass and add new tests as needed
4. **Keep PRs Focused** - One feature or fix per PR
5. **Describe Your Changes** - Use the PR template, explain what and why
6. **Request Review** - Tag appropriate reviewers
7. **Address Feedback** - Respond to review comments promptly
8. **Keep Updated** - Rebase on main if needed

### Pull Request Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] CHANGELOG.md updated
```

## Review Process

- All PRs require at least one approval from a maintainer
- Automated checks must pass (tests, linters, security scans)
- Large changes may require additional reviews
- Maintainers may request changes or provide feedback
- Be patient and respectful during the review process

## Release Process

Releases are automated using [release-please](https://github.com/googleapis/release-please):

1. **Automatic Release PRs** - When code changes are pushed to `main`, release-please:
   - Analyzes commit messages since last release
   - Determines version bump based on commit types
   - Creates/updates a Release PR with changelog

2. **Release Creation** - When Release PR is merged:
   - Creates GitHub release with tag
   - Includes auto-generated changelog
   - Follows [Semantic Versioning](https://semver.org/)

3. **Triggers** - Only code changes trigger releases:
   - ✅ docker-compose files, Dockerfiles, scripts, configs
   - ❌ Documentation (*.md), LICENSE, templates, editor configs

**Note:** Documentation-only changes do NOT create releases

## Community

- **GitHub Discussions** - For questions and general discussion
- **GitHub Issues** - For bug reports and feature requests
- **Pull Requests** - For code contributions

## Recognition

Contributors are recognized in:

- CHANGELOG.md for each release
- GitHub contributors page
- Special acknowledgements for significant contributions

## Questions?

If you have questions about contributing:

- Check existing documentation
- Search closed issues
- Ask in GitHub Discussions
- Open a new issue with the "question" label

## Licence

By contributing to AAX, you agree that your contributions will be licensed under the Apache License 2.0.

Thank you for contributing to AAX! 🎉
