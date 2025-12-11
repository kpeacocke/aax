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

.PHONY: build-dev-tools
build-dev-tools: build-ee-base ## Build Ansible development tools image
	@echo "Building dev-tools image..."
	docker build $(BUILD_ARGS) -t $(REGISTRY)/dev-tools:$(VERSION) -t $(REGISTRY)/dev-tools:latest images/dev-tools/
	@echo "Built $(REGISTRY)/dev-tools:$(VERSION)"

.PHONY: test-dev-tools
test-dev-tools: build-dev-tools ## Test dev-tools image
	@echo "Testing dev-tools image..."
	@docker run --rm $(REGISTRY)/dev-tools:latest ansible-navigator --version
	@docker run --rm $(REGISTRY)/dev-tools:latest ansible-lint --version
	@docker run --rm $(REGISTRY)/dev-tools:latest ansible --version
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
build-images: build-ee-base build-ee-builder build-dev-tools ## Build all images
	@echo "All images built successfully"

.PHONY: test-all
test-all: test-ee-base test-ee-builder test-dev-tools test ## Build and test all images
	@echo "All tests passed successfully"

.PHONY: ci
ci: lint-dockerfiles test-all ## Run full CI pipeline locally
	@echo "✓ CI pipeline completed successfully"

.PHONY: compose-build
compose-build: ## Build all images using docker-compose
	@echo "Building images with docker-compose..."
	BUILD_DATE=$(BUILD_DATE) VCS_REF=$(VCS_REF) VERSION=$(VERSION) docker compose build
	@echo "✓ All images built with docker-compose"

.PHONY: compose-up
compose-up: ## Start all services with docker-compose
	@echo "Starting services with docker-compose..."
	BUILD_DATE=$(BUILD_DATE) VCS_REF=$(VCS_REF) VERSION=$(VERSION) docker compose up -d
	@echo "✓ Services started"

.PHONY: compose-down
compose-down: ## Stop all services with docker-compose
	@echo "Stopping services with docker-compose..."
	docker compose down
	@echo "✓ Services stopped"

.PHONY: compose-logs
compose-logs: ## View logs from all services
	docker compose logs -f

.PHONY: compose-ps
compose-ps: ## Show status of all services
	docker compose ps

.PHONY: k8s-deploy
k8s-deploy: ## Deploy to Kubernetes using kustomize
	@echo "Deploying to Kubernetes..."
	kubectl apply -k k8s/
	@echo "✓ Deployed to Kubernetes"

.PHONY: k8s-delete
k8s-delete: ## Delete Kubernetes deployment
	@echo "Deleting Kubernetes deployment..."
	kubectl delete namespace aax
	@echo "✓ Kubernetes deployment deleted"

.PHONY: k8s-status
k8s-status: ## Show status of Kubernetes deployment
	@echo "Kubernetes deployment status:"
	@kubectl get all -n aax

.PHONY: k8s-logs
k8s-logs: ## View logs from Kubernetes pods
	@echo "Select deployment to view logs:"
	@echo "1) ee-base"
	@echo "2) ee-builder"
	@echo "3) dev-tools"
	@read -p "Enter choice [1-3]: " choice; \
	case $$choice in \
		1) kubectl logs -n aax -l app=ee-base -f ;; \
		2) kubectl logs -n aax -l app=ee-builder -f ;; \
		3) kubectl logs -n aax -l app=dev-tools -f ;; \
		*) echo "Invalid choice" ;; \
	esac

.PHONY: k8s-exec
k8s-exec: ## Execute shell in Kubernetes pod
	@echo "Select deployment to exec into:"
	@echo "1) ee-base"
	@echo "2) ee-builder"
	@echo "3) dev-tools"
	@read -p "Enter choice [1-3]: " choice; \
	case $$choice in \
		1) kubectl exec -it -n aax deployment/ee-base -- /bin/bash ;; \
		2) kubectl exec -it -n aax deployment/ee-builder -- /bin/bash ;; \
		3) kubectl exec -it -n aax deployment/dev-tools -- /bin/bash ;; \
		*) echo "Invalid choice" ;; \
	esac

.PHONY: k8s-test
k8s-test: ## Test Kubernetes deployment functionality
	@echo "Testing Kubernetes deployment..."
	@kubectl exec -n aax deployment/ee-base -- ansible --version
	@kubectl exec -n aax deployment/ee-builder -- ansible-builder --version
	@kubectl exec -n aax deployment/dev-tools -- ansible-navigator --version
	@kubectl exec -n aax deployment/dev-tools -- ansible-lint --version
	@echo "✓ All Kubernetes tests passed"

.PHONY: k8s-restart
k8s-restart: ## Restart all Kubernetes deployments
	@echo "Restarting Kubernetes deployments..."
	kubectl rollout restart deployment -n aax
	@echo "✓ Deployments restarted"
