.PHONY: help bootstrap test lint compose-up-controller compose-up-hub compose-up-eda compose-build compose-down upstream-build devel-up

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
PRE_COMMIT := $(VENV)/bin/pre_commit

help:
	@echo "Available targets:"
	@echo "  bootstrap            Create the local Python environment and install repo tooling"
	@echo "  test                 Run repo policy and docs checks"
	@echo "  lint                 Run pre-commit hooks across the repo"
	@echo "  upstream-build       Clone the upstream build sources for AWX, EE, and related projects"
	@echo "  compose-up-controller  Start the controller profile"
	@echo "  compose-up-hub       Start the hub profile"
	@echo "  compose-up-eda       Start the EDA profile"
	@echo "  compose-build        Build all configured images"
	@echo "  compose-down         Stop and remove the stack"
		@echo "  devel-up             Deploy the locally built upstream devel bundle"

bootstrap:
	@./scripts/bootstrap.sh

test:
	@$(PYTEST) -q tests/test_repo_policy.py tests/test_docs_contract.py

lint:
	@$(PRE_COMMIT) run --all-files

compose-up-controller:
	@docker compose --profile controller up -d

compose-up-hub:
	@docker compose --profile hub up -d

compose-up-eda:
	@docker compose --profile eda up -d

upstream-build:
	@bash scripts/build-upstream.sh

compose-build:
	@docker compose --profile controller --profile hub build

compose-down:
	@docker compose down

devel-up:
		@./scripts/deploy-devel.sh
