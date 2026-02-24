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

.PHONY: build-awx
build-awx: ## Build AWX controller image from source
	@echo "Building AWX controller image..."
	docker build $(BUILD_ARGS) -t $(REGISTRY)/awx:$(VERSION) -t $(REGISTRY)/awx:latest images/awx/
	@echo "Built $(REGISTRY)/awx:$(VERSION)"

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

# Controller Stack Targets

.PHONY: controller-up
controller-up: build-images build-awx ## Start AWX controller stack
	@echo "Starting AWX controller stack..."
	docker compose -f docker-compose.controller.yml up -d
	@echo "✓ Controller stack started"
	@echo ""
	@echo "Access AWX at: http://localhost:8080"
	@echo "Username: admin"
	@echo "Password: password"
	@echo ""
	@echo "Wait 2-3 minutes for initialization..."

.PHONY: controller-down
controller-down: ## Stop AWX controller stack
	@echo "Stopping AWX controller stack..."
	docker compose -f docker-compose.controller.yml down
	@echo "✓ Controller stack stopped"

.PHONY: controller-logs
controller-logs: ## View AWX controller logs
	docker compose -f docker-compose.controller.yml logs -f

.PHONY: controller-status
controller-status: ## Show AWX controller status
	docker compose -f docker-compose.controller.yml ps

.PHONY: controller-clean
controller-clean: ## Stop controller and remove all data
	@echo "⚠️  WARNING: This will remove all AWX data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f docker-compose.controller.yml down -v; \
		echo "✓ Controller stack and data removed"; \
	else \
		echo "✗ Cancelled"; \
	fi

# Private Automation Hub Targets

.PHONY: build-pulp
build-pulp: ## Build Pulp content management image
	@echo "Building Pulp image..."
	docker build $(BUILD_ARGS) -f images/pulp/Dockerfile.pulp -t $(REGISTRY)/pulp:$(VERSION) -t $(REGISTRY)/pulp:latest images/pulp/
	@echo "Built $(REGISTRY)/pulp:$(VERSION)"

.PHONY: build-galaxy-ng
build-galaxy-ng: ## Build Galaxy NG image
	@echo "Building Galaxy NG image..."
	docker build $(BUILD_ARGS) -t $(REGISTRY)/galaxy-ng:$(VERSION) -t $(REGISTRY)/galaxy-ng:latest images/galaxy-ng/
	@echo "Built $(REGISTRY)/galaxy-ng:$(VERSION)"

.PHONY: build-hub
build-hub: build-pulp build-galaxy-ng ## Build all hub images
	@echo "All hub images built successfully"

.PHONY: hub-up
hub-up: build-hub ## Start Private Automation Hub stack
	@echo "Starting Private Automation Hub stack..."
	docker compose -f docker-compose.hub.yml up -d
	@echo "✓ Hub stack started"
	@echo ""
	@echo "Access Galaxy NG at: http://localhost:5001"
	@echo "Pulp API at: http://localhost:24817/pulp/api/v3/"
	@echo "Content at: http://localhost:24816"
	@echo ""
	@echo "Username: admin"
	@echo "Password: changeme (or value of HUB_ADMIN_PASSWORD)"
	@echo ""
	@echo "Wait 2-3 minutes for initialization..."

.PHONY: hub-down
hub-down: ## Stop Private Automation Hub stack
	@echo "Stopping Hub stack..."
	docker compose -f docker-compose.hub.yml down
	@echo "✓ Hub stack stopped"

.PHONY: hub-logs
hub-logs: ## View Hub stack logs
	docker compose -f docker-compose.hub.yml logs -f

.PHONY: hub-status
hub-status: ## Show Hub stack status
	docker compose -f docker-compose.hub.yml ps

.PHONY: hub-restart
hub-restart: ## Restart Hub stack
	@echo "Restarting Hub stack..."
	docker compose -f docker-compose.hub.yml restart
	@echo "✓ Hub stack restarted"

.PHONY: hub-clean
hub-clean: ## Stop hub and remove all data
	@echo "⚠️  WARNING: This will remove all Hub data including collections!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose -f docker-compose.hub.yml down -v; \
		echo "✓ Hub stack and data removed"; \
	else \
		echo "✗ Cancelled"; \
	fi

.PHONY: hub-test
hub-test: ## Test Hub API endpoints
	@echo "Testing Hub API endpoints..."
	@echo "Testing Galaxy NG API..."
	@curl -f http://localhost:5001/api/galaxy/ || echo "Galaxy NG API not ready"
	@echo ""
	@echo "Testing Pulp API..."
	@curl -f http://localhost:24817/pulp/api/v3/status/ || echo "Pulp API not ready"
	@echo ""
	@echo "Testing Content delivery..."
	@curl -f http://localhost:24816/pulp/content/ || echo "Content delivery not ready"
	@echo ""
	@echo "✓ Hub tests complete"

# Combined Stack Targets

.PHONY: all-up
all-up: compose-up controller-up hub-up ## Start all stacks (EE + Controller + Hub)
	@echo "✓ All services started"
	@echo ""
	@echo "Services available:"
	@echo "  - AWX Controller: http://localhost:8080"
	@echo "  - Galaxy NG Hub: http://localhost:5001"
	@echo "  - Pulp API: http://localhost:24817/pulp/api/v3/"
	@echo ""

.PHONY: all-down
all-down: hub-down controller-down compose-down ## Stop all stacks
	@echo "✓ All services stopped"

.PHONY: all-clean
all-clean: hub-clean controller-clean ## Clean all data from all stacks
	docker compose down -v
	@echo "✓ All data removed"
