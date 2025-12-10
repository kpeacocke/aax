# Makefile for AAX project
# Provides convenient shortcuts for common development tasks

# Image build variables
VERSION ?= dev
BUILD_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
REGISTRY ?= aax
BUILD_ARGS := --build-arg VERSION=$(VERSION) \
	--build-arg BUILD_DATE=$(BUILD_DATE) \
	--build-arg VCS_REF=$(VCS_REF)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: build-ee-base
build-ee-base: ## Build Ansible EE base image
	@echo "Building ee-base image..."
	docker build $(BUILD_ARGS) -t $(REGISTRY)/ee-base:$(VERSION) -t $(REGISTRY)/ee-base:latest images/ee-base/
	@echo "Built $(REGISTRY)/ee-base:$(VERSION)"

.PHONY: test-ee-base
test-ee-base: build-ee-base ## Test ee-base image
	@echo "Testing ee-base image..."
	@docker run --rm $(REGISTRY)/ee-base:latest ansible --version
	@docker run --rm $(REGISTRY)/ee-base:latest ansible-runner --version
	@echo "✓ All tests passed"

.PHONY: build-ee-builder
build-ee-builder: build-ee-base ## Build Ansible EE builder image
	@echo "Building ee-builder image..."
	docker build $(BUILD_ARGS) -t $(REGISTRY)/ee-builder:$(VERSION) -t $(REGISTRY)/ee-builder:latest images/ee-builder/
	@echo "Built $(REGISTRY)/ee-builder:$(VERSION)"

.PHONY: test-ee-builder
test-ee-builder: build-ee-builder ## Test ee-builder image
	@echo "Testing ee-builder image..."
	@docker run --rm $(REGISTRY)/ee-builder:latest ansible-builder --version
	@docker run --rm $(REGISTRY)/ee-builder:latest ansible --version
	@echo "✓ All tests passed"

.PHONY: lint-dockerfiles
lint-dockerfiles: ## Lint all Dockerfiles with hadolint
	@find images -name "Dockerfile" -exec hadolint {} \;

.PHONY: test
test: ## Run pytest tests for all images
	@echo "Running pytest tests..."
	pytest tests/ -v

.PHONY: test-fast
test-fast: ## Run pytest tests without rebuilding images
	@echo "Running pytest tests (skipping builds)..."
	pytest tests/ -v --no-cov

.PHONY: build-images
build-images: build-ee-base build-ee-builder ## Build all images
	@echo "All images built successfully"

.PHONY: test-all
test-all: test-ee-base test-ee-builder test ## Build and test all images
	@echo "All tests passed successfully"

.PHONY: ci
ci: lint-dockerfiles test-all ## Run full CI pipeline locally
	@echo "✓ CI pipeline completed successfully"
