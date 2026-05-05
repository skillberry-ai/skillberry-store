# ============================================================================
# Skillberry Store - Simplified Makefile
# ============================================================================
# This Makefile provides all essential build, test, and deployment targets
# in a single, easy-to-understand file.
#
# Quick Start:
#   make help          - Show all available targets
#   make install       - Install dependencies
#   make test          - Run tests
#   make run           - Start the service
#   make docker-build  - Build Docker image
#
# For detailed documentation, see: docs/MAKE_SYSTEM.md
# ============================================================================

.DEFAULT_GOAL := help

# ============================================================================
# Project Configuration
# ============================================================================
# Load project-specific settings from .mk/local.mk
include .mk/local.mk

# ============================================================================
# System Detection
# ============================================================================
ARCH := $(shell uname -m)
OS := $(shell uname -s)

# Detect Docker or Podman
DOCKER := docker
ifeq ($(shell command -v podman 2>/dev/null),)
    DOCKER := docker
else
    DOCKER := podman
endif

# ============================================================================
# Version Management
# ============================================================================
# Automatically generate version from git state
# Format: 0.5.3 or 0.5.3-5-gc9b7ddd or 0.5.3-5-gc9b7ddd-dirty

_LATEST_RELEASE := $(shell git branch -r 2>/dev/null | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 1)
_CURRENT_COMMIT := $(shell git rev-parse --short=7 HEAD 2>/dev/null || echo "unknown")
_DIRTY := $(shell git diff --quiet 2>/dev/null || echo "-dirty")

ifeq ($(_LATEST_RELEASE),)
    # No release exists yet - use commit hash only
    BUILD_VERSION := g$(_CURRENT_COMMIT)$(_DIRTY)
else
    # Calculate commits since last release
    _COMMIT_COUNT := $(shell git rev-list --count $(_LATEST_RELEASE)..HEAD 2>/dev/null || echo "0")
    ifeq ($(_COMMIT_COUNT),0)
        BUILD_VERSION := $(_LATEST_RELEASE)$(_DIRTY)
    else
        BUILD_VERSION := $(_LATEST_RELEASE)-$(_COMMIT_COUNT)-g$(_CURRENT_COMMIT)$(_DIRTY)
    endif
endif

BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

# ============================================================================
# Service Configuration
# ============================================================================
# Convert service name to different formats
SERVICE_NAME_LC := $(shell echo $(SERVICE_NAME) | tr '[:upper:]' '[:lower:]')
SERVICE_NAME_CN := $(shell echo $(SERVICE_NAME_LC) | tr '-' '_')
ACRONYM_LC := $(shell echo $(ACRONYM) | tr '[:upper:]' '[:lower:]')

# Extract main service port (first in the list)
MAIN_SERVICE_PORT := $(firstword $(SERVICE_PORTS))

# Service process management
SERVICE_SENTINEL := /tmp/$(SERVICE_NAME)-service.pid
SERVICE_LOG := /tmp/$(SERVICE_NAME).log

# ============================================================================
# Docker Configuration
# ============================================================================
REGISTRY_HOST ?= ghcr.io
DOCKER_PROJECT ?= skillberry-ai
REPOSITORY_NAME := $(REGISTRY_HOST)/$(DOCKER_PROJECT)

# Base image configuration
BASE_IMAGE_NAME := skillberry-base
BASE_IMAGE_TAG := latest
BASE_IMAGE_FULL_NAME := $(REPOSITORY_NAME)/$(BASE_IMAGE_NAME)

# Service image configuration
IMAGE_NAME := $(SERVICE_NAME)
IMAGE_TAG := $(BUILD_VERSION)
FULL_IMAGE_NAME := $(REPOSITORY_NAME)/$(IMAGE_NAME)

# Docker build target: "local" or "registry"
DBT ?= local

# Supported architectures for multi-platform builds
SUPPORTED_ARCHS := linux/amd64 linux/arm64

# ============================================================================
# Directory Setup
# ============================================================================
# Create .stamps directory for tracking build state
_ := $(shell mkdir -p .stamps)

# ============================================================================
# Help Target
# ============================================================================
.PHONY: help
help: ## Show this help message
	@echo "Skillberry Store - Available Make Targets"
	@echo "=========================================="
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n\n"} \
		/^[a-zA-Z_-]+:.*?##/ { \
			printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 \
		} \
		/^##@/ { \
			printf "\n\033[1m%s\033[0m\n", substr($$0, 5) \
		}' $(MAKEFILE_LIST)
	@echo ""
	@echo "For detailed documentation, see: docs/MAKE_SYSTEM.md"

# ============================================================================
##@ Development
# ============================================================================

.PHONY: install
install: check-venv update-git-version .stamps/install-$(ODEPS) ## Install dependencies (use ODEPS=dev for dev dependencies)
	@echo "✓ Dependencies installed successfully"

.stamps/install-$(ODEPS): pyproject.toml
	@echo "Installing dependencies..."
	@python -m pip install -q --upgrade pip uv
	@if [ -z "$(ODEPS)" ]; then \
		uv pip install -e .; \
	else \
		uv pip install -e .[$(ODEPS)]; \
	fi
	@touch .stamps/install-$(ODEPS)

.PHONY: check-venv
check-venv: ## Check if running in a virtual environment
	@python -c "import sys, os; \
		in_venv = ('VIRTUAL_ENV' in os.environ) or \
		          (hasattr(sys, 'real_prefix') or \
		          (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)); \
		print('✅ In virtual environment' if in_venv else '❌ Not in virtual environment'); \
		exit(0 if in_venv else 1)"

.PHONY: update-git-version
update-git-version: ## Update git version file
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
		NEW_CONTENT="__git_version__ = \"$(BUILD_VERSION)\""; \
		if [ ! -f "$(VERSION_LOCATION)" ] || [ "$$(cat $(VERSION_LOCATION) 2>/dev/null)" != "$$NEW_CONTENT" ]; then \
			echo "Updating git version: $(BUILD_VERSION)"; \
			echo "$$NEW_CONTENT" > $(VERSION_LOCATION); \
		fi; \
	fi

.PHONY: test
test: install ## Run unit tests
	@echo "Running unit tests..."
	@pytest

# Note: test-e2e and lint targets are defined in .mk/dev.mk
# This allows project-specific customization

.PHONY: format
format: install ## Auto-format code
	@echo "Formatting code..."
	@black src/skillberry_store/
	@echo "✓ Code formatted"

# ============================================================================
##@ Service Management
# ============================================================================

.PHONY: run
run: install .stamps/srv.env ## Start the service locally
	@if [ -f $(SERVICE_SENTINEL) ]; then \
		echo "⚠ Service already running (PID: $$(cat $(SERVICE_SENTINEL)))"; \
		echo "  Use 'make stop' to stop it first"; \
		exit 1; \
	fi
	@echo "Starting $(SERVICE_NAME) service (version $(BUILD_VERSION))..."
	@set -a; source .stamps/srv.env; set +a; \
	nohup python -m $(SERVICE_ENTRY_MODULE) > $(SERVICE_LOG) 2>&1 & \
	echo $$! > $(SERVICE_SENTINEL)
	@echo "✓ Service started (PID: $$(cat $(SERVICE_SENTINEL)))"
	@echo "  Logs: $(SERVICE_LOG)"

.PHONY: stop
stop: ## Stop the service
	@if [ ! -f $(SERVICE_SENTINEL) ]; then \
		echo "⚠ Service not running"; \
		exit 0; \
	fi
	@echo "Stopping $(SERVICE_NAME) service..."
	@PID=$$(cat $(SERVICE_SENTINEL)); \
	if kill -0 $$PID 2>/dev/null; then \
		kill $$PID; \
		echo "✓ Service stopped"; \
	else \
		echo "⚠ Service process not found"; \
	fi
	@rm -f $(SERVICE_SENTINEL)

.PHONY: clean
clean: stop ## Stop service and clean temporary files
	@echo "Cleaning temporary files..."
	@rm -f $(SERVICE_LOG)
	@rm -rf __pycache__ .pytest_cache
	@rm -rf build dist *.egg-info
	@echo "✓ Cleaned"

# Note: clean-service-data target is defined in .mk/process.mk
# This allows project-specific customization of data cleanup

# Generate service environment variables file
.stamps/srv.env: .mk/local.mk
	@echo "Generating service environment variables..."
	@echo "# Auto-generated service environment variables" > .stamps/srv.env
	@i=1; \
	for port in $(SERVICE_PORTS); do \
		role=$$(echo $(SERVICE_PORT_ROLES) | cut -d' ' -f$$i); \
		echo "$(ACRONYM)_$${role}_PORT=$$port" >> .stamps/srv.env; \
		i=$$((i + 1)); \
	done
	@echo "$(ACRONYM)_HOST=$(SERVICE_HOST)" >> .stamps/srv.env

# ============================================================================
##@ Docker Operations
# ============================================================================

.PHONY: docker-build
docker-build: update-git-version ## Build Docker image locally
	@echo "Building Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	@echo "  Version: $(BUILD_VERSION)"
	@echo "  Date: $(BUILD_DATE)"
	@$(DOCKER) build \
		--file Dockerfile \
		--build-arg BASE_IMAGE_FULL_NAME=$(BASE_IMAGE_FULL_NAME) \
		--build-arg BASE_IMAGE_TAG=$(BASE_IMAGE_TAG) \
		--build-arg BUILD_VERSION=$(BUILD_VERSION) \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg SERVICE_NAME="$(SERVICE_NAME)" \
		--build-arg SERVICE_PORTS="$(SERVICE_PORTS)" \
		--build-arg SERVICE_ENTRY_MODULE="$(SERVICE_ENTRY_MODULE)" \
		-t $(FULL_IMAGE_NAME):$(IMAGE_TAG) \
		-t $(FULL_IMAGE_NAME):latest \
		.
	@echo "✓ Docker image built successfully"

.PHONY: docker-run
docker-run: docker-build docker-clean ## Run service in Docker container
	@echo "Starting Docker container: $(SERVICE_NAME)"
	@test -f .env || touch .env
	@$(DOCKER) run --name $(SERVICE_NAME) \
		--env-file .env \
		-d \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "✓ Docker container started"
	@echo "  Container: $(SERVICE_NAME)"
	@echo "  Image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"

.PHONY: docker-stop
docker-stop: ## Stop Docker container
	@echo "Stopping Docker container: $(SERVICE_NAME)"
	@$(DOCKER) stop $(SERVICE_NAME) 2>/dev/null || true
	@echo "✓ Container stopped"

.PHONY: docker-clean
docker-clean: docker-stop ## Remove Docker container
	@echo "Removing Docker container: $(SERVICE_NAME)"
	@$(DOCKER) rm -f $(SERVICE_NAME) 2>/dev/null || true
	@echo "✓ Container removed"

.PHONY: docker-rmi
docker-rmi: docker-clean ## Remove Docker image and container
	@echo "Removing Docker images..."
	@$(DOCKER) rmi -f $(FULL_IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	@$(DOCKER) rmi -f $(FULL_IMAGE_NAME):latest 2>/dev/null || true
	@echo "✓ Images removed"

.PHONY: docker-pull
docker-pull: ## Pull latest Docker image from registry
	@echo "Pulling Docker image: $(FULL_IMAGE_NAME):latest"
	@$(DOCKER) pull $(FULL_IMAGE_NAME):latest
	@$(DOCKER) tag $(FULL_IMAGE_NAME):latest $(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "✓ Image pulled and tagged"

.PHONY: docker-logs
docker-logs: ## Show Docker container logs
	@$(DOCKER) logs -f $(SERVICE_NAME)

# ============================================================================
##@ Release Management
# ============================================================================

.PHONY: release
release: check-git-clean check-git-main ## Create a new release (requires RELEASE_VERSION=x.y.z)
	@if [ -z "$(RELEASE_VERSION)" ]; then \
		echo "❌ RELEASE_VERSION not set"; \
		echo "Usage: make release RELEASE_VERSION=1.0.0"; \
		exit 1; \
	fi
	@echo "Creating release: $(RELEASE_VERSION)"
	@echo "⚠ This will create a tag and GitHub release. Continue? (Ctrl+C to cancel)"
	@sleep 5
	@git checkout -b branch-$(RELEASE_VERSION)
	@git tag -a $(RELEASE_VERSION) -m "Release $(RELEASE_VERSION)"
	@git push origin $(RELEASE_VERSION)
	@git checkout main
	@gh release create $(RELEASE_VERSION) --generate-notes
	@echo "✓ Release $(RELEASE_VERSION) created"

.PHONY: check-git-clean
check-git-clean: ## Check if git working directory is clean
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "❌ Uncommitted changes detected"; \
		git status --short; \
		exit 1; \
	fi

.PHONY: check-git-main
check-git-main: ## Check if on main branch
	@if [ "$$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" != "main" ]; then \
		echo "❌ Not on main branch"; \
		exit 1; \
	fi

# ============================================================================
##@ SDK Management
# ============================================================================

.PHONY: update-sdk
update-sdk: ## Update the SDK (if SERVICE_HAS_SDK=1)
	@if [ "$(SERVICE_HAS_SDK)" != "1" ]; then \
		echo "⚠ Service has no SDK (SERVICE_HAS_SDK != 1)"; \
		exit 0; \
	fi
	@echo "Updating SDK..."
	@$(MAKE) docker-run
	@echo "Waiting for service to start..."
	@timeout 120 bash -c 'until curl -sf http://$(SERVICE_HOST):$(MAIN_SERVICE_PORT)/docs > /dev/null; do sleep 5; done'
	@$(MAKE) generate-sdk
	@$(MAKE) docker-stop
	@echo "✓ SDK updated"

.PHONY: generate-sdk
generate-sdk: install ## Generate SDK from OpenAPI spec
	@echo "Generating SDK..."
	@mkdir -p client/python/$(SERVICE_NAME_CN)_sdk
	@rm -rf client/python/$(SERVICE_NAME_CN)_sdk/*
	@openapi-generator-cli generate \
		-i http://$(SERVICE_HOST):$(MAIN_SERVICE_PORT)/openapi.json \
		-g python \
		-o client/python/$(SERVICE_NAME_CN)_sdk \
		--package-name $(SERVICE_NAME_CN)_sdk
	@echo "✓ SDK generated"

# ============================================================================
##@ Utility Targets
# ============================================================================

.PHONY: show-version
show-version: ## Show current build version
	@echo $(BUILD_VERSION)

.PHONY: show-config
show-config: ## Show current configuration
	@echo "Project Configuration"
	@echo "===================="
	@echo "Asset Name:      $(ASSET_NAME)"
	@echo "Service Name:    $(SERVICE_NAME)"
	@echo "Version:         $(BUILD_VERSION)"
	@echo "Build Date:      $(BUILD_DATE)"
	@echo "Service Ports:   $(SERVICE_PORTS)"
	@echo "Service Host:    $(SERVICE_HOST)"
	@echo "Entry Module:    $(SERVICE_ENTRY_MODULE)"
	@echo "Docker Image:    $(FULL_IMAGE_NAME):$(IMAGE_TAG)"

.PHONY: clean-all
clean-all: clean docker-rmi ## Clean everything (service, Docker, temp files)
	@rm -rf .stamps
	@echo "✓ Everything cleaned"

# ============================================================================
# CI/CD Targets
# ============================================================================

.PHONY: ci-test
ci-test: lint test test-e2e ## Run all CI tests

.PHONY: ci-build
ci-build: docker-build ## Build for CI

# ============================================================================
# Include project-specific targets
# ============================================================================
-include .mk/dev.mk
-include .mk/process.mk