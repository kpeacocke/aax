# Makefile for AAX project
# Provides convenient shortcuts for common development tasks

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Initial setup - copy .env.example to .env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please update it with your configuration."; \
	else \
		echo ".env file already exists. Skipping..."; \
	fi
	@echo "Remember to edit .env with your actual configuration!"

.PHONY: build
build: ## Build all Docker images
	docker-compose build

.PHONY: up
up: ## Start all services
	docker-compose up -d

.PHONY: down
down: ## Stop all services
	docker-compose down

.PHONY: restart
restart: down up ## Restart all services

.PHONY: logs
logs: ## Show logs from all services
	docker-compose logs -f

.PHONY: ps
ps: ## Show running containers
	docker-compose ps

.PHONY: shell-web
shell-web: ## Open shell in AWX web container
	docker-compose exec awx_web /bin/bash

.PHONY: shell-db
shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U awx awx

.PHONY: health
health: ## Check health of all services
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "Checking AWX API..."
	@curl -f http://localhost:8080/api/v2/ping/ || echo "AWX not responding"

.PHONY: validate
validate: ## Validate docker-compose.yml
	docker-compose config --quiet

.PHONY: clean
clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/

.PHONY: backup
backup: ## Backup database
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U awx awx > backups/backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "Backup created in backups/ directory"

.PHONY: restore
restore: ## Restore database (usage: make restore FILE=backups/backup-20231201-120000.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required. Usage: make restore FILE=backups/backup-20231201-120000.sql"; \
		exit 1; \
	fiDocker resources and temporary files
	@echo "Cleaning up temporary files..."
	@find . -type f -name "*.log" -delete
	@find . -type f -name "*.tmp" -delete
	@echo "Done"e exec awx_web awx-manage collectstatic --noinput

.PHONY: createsuperuser
createsuperuser: ## Create Django superuser
	docker-compose exec awx_web awx-manage createsuperuser

.PHONY: prune
prune: ## Remove all stopped containers, unused networks, and dangling images
	docker system prune -f

.PHONY: prune-all
prune-all: ## Remove all Docker resources (WARNING: destructive)
	docker system prune -af --volumes

.PHONY: update
update: ## Pull latest images and restart
	docker-compose pull
	docker-compose up -d

.PHONY: validate
validate: lint test ## Run linters and tests

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files
config
config: ## Show docker-compose configuration
	docker-compose config

.DEFAULT_GOAL := help

.PHONY: init
init: setup ## Complete initial setup (alias for setup)
