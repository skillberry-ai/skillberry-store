# =============================================================================
# Development Targets
# =============================================================================
# This file contains common development targets used across all Skillberry projects.
# These targets handle dependency installation, testing, SDK generation, and releases.
#
# Key targets:
#   - install-requirements: Install Python dependencies with optional groups
#   - test: Run unit tests
#   - release: Create a new versioned release
#   - update-sdk: Generate Python SDK from OpenAPI specification
#   - lint: Check code formatting (project-specific)
# =============================================================================

##@ Development

# -----------------------------------------------------------------------------
# Python Version Support
# -----------------------------------------------------------------------------
# List of supported Python versions for this project
# Format: "major.minor" or "major.minor.patch" with optional "+" for minimum
# Examples: "3.11" "3.12.10" "3.11+" "3.12.5+"
SUPPORTED_PYTHON_VERSIONS := 3.11 3.12.10

# -----------------------------------------------------------------------------
# Service Name Transformations
# -----------------------------------------------------------------------------
# Generate different formats of the service name for various uses:
# - SERVICE_NAME_LC: lowercase (e.g., "skillberry-store")
# - SERVICE_NAME_CN: code notation - lowercase with underscores (e.g., "skillberry_store")
# - ACRONYM_LC: lowercase acronym (e.g., "sbs")
SERVICE_NAME_LC = $(shell printf "%s" "$(SERVICE_NAME)" | tr '[:upper:]' '[:lower:]')
SERVICE_NAME_CN ?= $(shell printf "%s" "$(SERVICE_NAME_LC)" | tr '-' '_')
ACRONYM_LC ?= $(shell echo $(ACRONYM) | tr '[:upper:]' '[:lower:]')

# -----------------------------------------------------------------------------
# API Configuration
# -----------------------------------------------------------------------------
# Configuration for API clients and SDK generation
RESTISH_CONFIG_APIS ?= $(HOME)/.config/restish/apis.json
OPEN_API_SPEC_URL ?= http://$(SERVICE_HOST):$(MAIN_SERVICE_PORT)

# Whether this service generates a Python SDK (0 or 1)
export SERVICE_HAS_SDK ?= 0

# -----------------------------------------------------------------------------
# Code Change Detection
# -----------------------------------------------------------------------------
# Define which directories contain code that should trigger rebuilds
# These are the "roots" of the code tree to monitor
CODE_SUBTREES := src .mk $(SB_COMMON_PATH)/.mk $(SB_COMMON_PATH)/scripts

# File patterns to consider as "code" for change detection
# Matches Python files, Makefiles, .mk files, and shell scripts
CODE_FILTER := \( -name '*.py' -o -name 'Makefile' -o -name '*.mk' -o -name '*.sh' \)

# Find all code files across all subtrees
# This creates a list of all files that should trigger a rebuild when changed
CODE_FILES := $(foreach T,$(CODE_SUBTREES), \
  $(shell find $(T) -type f $(CODE_FILTER) -print))

# Add additional important files that should trigger rebuilds
CODE_FILES := $(CODE_FILES) pyproject.toml Makefile Dockerfile

# Stamp file that tracks when code last changed
# This is used to determine if Docker images need rebuilding
.stamps/code-scan: $(CODE_FILES)
	@echo "Detected code changed in: $(CODE_SUBTREES)"
	@if [ -f .stamps/code-scan ]; then \
		for file in $(CODE_FILES); do \
			if [ "$$file" -nt .stamps/code-scan ]; then \
				echo "$$file"; \
			fi; \
		done; \
	fi
	@touch .stamps/code-scan

# -----------------------------------------------------------------------------
# Git Hooks Setup
# -----------------------------------------------------------------------------
# Configure git to use custom hooks from .githooks directory
# This allows project-specific pre-commit, pre-push, etc. hooks
git-hooks-setup:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    echo "Setting up Git hooks..."; \
	    git config core.hooksPath .githooks; \
	    chmod +x .githooks/*; \
	else \
	    echo "Skipping git-hooks-setup: not inside a Git repository."; \
	fi

# -----------------------------------------------------------------------------
# Service Environment Display
# -----------------------------------------------------------------------------
.PHONY: show-srv-env
show-srv-env: .stamps/srv.env	## Show service env (ports, host)
	@cat .stamps/srv.env

# -----------------------------------------------------------------------------
# Testing
# -----------------------------------------------------------------------------
test: install-requirements ## Test the tools-service
	pytest

# -----------------------------------------------------------------------------
# Release Validation
# -----------------------------------------------------------------------------
# Ensure there are no uncommitted changes before releasing
# This prevents accidentally releasing with local modifications
check-git-clean:
	@changes="$$(git status --porcelain)"; \
	if [ -n "$$changes" ]; then \
	  echo "! You have uncommitted changes. Please commit, stash or clean them before releasing."; \
	  echo "=== Changes ==="; \
	  echo "$$changes"; \
	  exit 1; \
	fi

# Ensure we're on the main branch before releasing
# Releases should only be created from the main branch
check-git-main:
	@if [ "$(shell git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
		echo "! You must be on the main branch to run this command"; \
		exit 1; \
	fi

# -----------------------------------------------------------------------------
# Dependency Installation
# -----------------------------------------------------------------------------
# Install Python dependencies with optional dependency groups
# Usage:
#   make install-requirements              # Install base dependencies
#   make install-requirements ODEPS=dev    # Install with dev dependencies
#   make install-requirements ODEPS=dev,vllm  # Install multiple groups
.PHONY: install-requirements verify-venv
install-requirements: update-git-version git-hooks-setup verify-venv .stamps/install-requirements-$(ODEPS) ## Install dependencies. For opt. deps: make install-requirements ODEPS=dev,vllm
	@true

# Verify we're in a virtual environment and have correct Python version
verify-venv:
	@$(SB_COMMON_PATH)/scripts/check_venv.sh $(SUPPORTED_PYTHON_VERSIONS) || exit 1
	@python $(SB_COMMON_PATH)/scripts/ensure_pip.py || exit 1
	@python -m pip install uv

# Only actually install when pyproject.toml changes
# This stamp file tracks which optional dependencies were last installed
.stamps/install-requirements-$(ODEPS): pyproject.toml .venv
	@ODEPS="$(ODEPS)"; \
	if [ -z "$$ODEPS" ]; then \
		uv pip install -e .; \
	else \
		uv pip install -e .[$(ODEPS)]; \
	fi
	@touch .stamps/install-requirements-$(ODEPS)

# -----------------------------------------------------------------------------
# Git Version Management
# -----------------------------------------------------------------------------
# Update the git version file if it doesn't exist or has changed
# This embeds the current BUILD_VERSION into the Python package
# The version is calculated in globals.mk based on git history
.PHONY: update-git-version
update-git-version:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    NEW_CONTENT="__git_version__ = \"$(BUILD_VERSION)\""; \
	    if [ ! -f "$(VERSION_LOCATION)" ]; then \
	        echo "Creating git version file at $(VERSION_LOCATION)"; \
	        echo "$$NEW_CONTENT" > $(VERSION_LOCATION); \
	    else \
	        CURRENT_CONTENT=$$(cat $(VERSION_LOCATION) 2>/dev/null || echo ""); \
	        if [ "$$CURRENT_CONTENT" != "$$NEW_CONTENT" ]; then \
				echo "Git version changed. Current content: $$CURRENT_CONTENT <==> New content: $$NEW_CONTENT"; \
	            echo "Updating git version in $(VERSION_LOCATION)"; \
	            echo "$$NEW_CONTENT" > $(VERSION_LOCATION); \
	        else \
	            echo "Git version in $(VERSION_LOCATION) is already up to date"; \
	        fi; \
	    fi; \
	else \
	    echo "Skipping update-git-version: not inside a Git repository."; \
	fi

# -----------------------------------------------------------------------------
# Release Process
# -----------------------------------------------------------------------------
# Create a new release with the specified version
# This is a comprehensive process that:
# 1. Validates the environment (main branch, no uncommitted changes)
# 2. Creates a release branch (branch-X.Y.Z)
# 3. Creates and pushes a git tag
# 4. Creates a GitHub release with auto-generated notes
# 5. Builds and pushes Docker images
#
# Usage: RELEASE_VERSION=1.2.3 make release
release: check-git-main check-git-clean install-requirements  ## Release a new version
	@if [ -z "$(RELEASE_VERSION)" ]; then \
		echo "++++++++++++++++++++++++++++++++++++++++++++"; \
  		echo "RELEASE_VERSION is not set. It is required for the release"; \
  		echo "Please set RELEASE_VERSION and use 'RELEASE_VERSION=<version> make release' "; \
		echo "++++++++++++++++++++++++++++++++++++++++++++"; \
	exit 1; fi

	@command -v sed >/dev/null 2>&1 || { echo "❌ 'sed' is not installed. Aborting."; exit 1; }
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Creating release with version: $(RELEASE_VERSION)"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@sleep 10
	@echo "===> Generating git tag $(RELEASE_VERSION) and creating GitHub release"
	@git checkout -b branch-$(RELEASE_VERSION)
	@echo "===> Generated release branch $(RELEASE_VERSION)"
	@git tag -a $(RELEASE_VERSION) -m "Release $(RELEASE_VERSION)" 
	@git push origin $(RELEASE_VERSION)

	# Switch back to main so update-git-version works correctly
	@git checkout main

	# Create GitHub release with auto-generated or explicit notes
	# If no previous release exists, use GitHub's auto-generated notes
	# If a previous release exists, generate notes from commit range
	@REL_PREV_RELEASE=$$(git branch -r | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 2 | head -n 1); \
	if [ -z "$$REL_PREV_RELEASE" ] || [ "$$REL_PREV_RELEASE" = "$(RELEASE_VERSION)" ]; then \
		echo "No previous release found. Creating release with generated notes..."; \
		gh release create $(RELEASE_VERSION) --generate-notes; \
	else \
		echo "Previous release found: $$REL_PREV_RELEASE"; \
		REL_CURRENT_COMMIT=$$(git rev-parse --short=7 HEAD); \
		REL_PREV_COMMIT=$$(git merge-base origin/main origin/branch-$$REL_PREV_RELEASE); \
		echo "Creating release from $$REL_PREV_COMMIT to $$REL_CURRENT_COMMIT..."; \
		gh release create $(RELEASE_VERSION) --title "$(RELEASE_VERSION)" --notes "$$(git log --pretty=format:'- %s by %an' $$REL_PREV_COMMIT..$$REL_CURRENT_COMMIT)"; \
	fi

	# Switch to release branch for Docker build with customized dependencies
	@git checkout branch-$(RELEASE_VERSION)

	@echo "===> Building and pushing new docker image"
	@make docker-push
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Release $(RELEASE_VERSION) created successfully"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"

# -----------------------------------------------------------------------------
# SDK Generation and Update
# -----------------------------------------------------------------------------
# Update the Python SDK if the service has one
# This target:
# 1. Starts the service in Docker
# 2. Waits for it to be ready
# 3. Generates SDK from the OpenAPI spec
# 4. Commits changes if any
# 5. Stops the service
update-sdk: ## Update the SDK, if needed
	@if [ "$$SERVICE_HAS_SDK" = "1" ]; then \
		rm -rf /tmp/skillberry-sdk || true; \
		echo "==> Updating SDK..."; \
		make docker-run; \
		timeout 120 bash -c 'until curl -sf $(OPEN_API_SPEC_URL)/docs > /dev/null; do echo "Waiting for $(DESC_NAME)..."; sleep 5; done'; \
		echo "$(DESC_NAME) started (using docker)"; \
		make generate-sdk && \
		echo "SDK updated successfully" && \
		git add . && \
		if git diff --cached --quiet; then \
			echo "!!! No updates to commit !!!"; \
		else \
			echo "!!! Updates detected, committing... !!!"; \
			git commit -m "Update $(SERVICE_NAME_CN)_sdk $$(date '+%Y-%m-%d %H:%M:%S')"; \
		fi; \
		make docker-stop; \
		echo "$(DESC_NAME) stopped"; \
		echo "==> SDK update completed successfully"; \
	else \
		echo "Service has no SDK, skipping"; \
	fi

# Directory where the Python SDK is generated
PYTHON_SDK_DIR = client/python/$(SERVICE_NAME_CN)_sdk

# Generate Python SDK from OpenAPI specification
# This uses openapi-generator-cli to create a complete Python client
# Then adds a CLI module for command-line access
generate-sdk: install-requirements # Generate SDK
	@mkdir -p $(PYTHON_SDK_DIR)
	@rm -fr $(PYTHON_SDK_DIR)/*
	@openapi-generator-cli generate -i $(OPEN_API_SPEC_URL)/openapi.json \
		-g python \
		-o $(PYTHON_SDK_DIR) \
		--package-name $(SERVICE_NAME_CN)_sdk
	@echo "==> Adding CLI module to SDK..."
	@sed -e 's|{{API_NAME}}|$(ACRONYM_LC)|g' \
	     -e 's|{{API_URL}}|$(OPEN_API_SPEC_URL)|g' \
	     $(SB_COMMON_PATH)/scripts/sdk_cli.py > $(PYTHON_SDK_DIR)/$(SERVICE_NAME_CN)_sdk/sdk_cli.py
	@echo "==> Backing up setup.py and pyproject.toml"; \
		cp $(PYTHON_SDK_DIR)/setup.py $(PYTHON_SDK_DIR)/setup.py.bak; \
		cp $(PYTHON_SDK_DIR)/pyproject.toml $(PYTHON_SDK_DIR)/pyproject.toml.bak;
	@echo "==> Updating setup.py to add CLI entry point..."
	@sed -i '/package_data=/i\    entry_points={\n        "console_scripts": [\n            "$(ACRONYM_LC)=$(SERVICE_NAME_CN)_sdk.sdk_cli:cli",\n        ],\n    },' $(PYTHON_SDK_DIR)/setup.py
	@echo "==> Fixing pyproject.toml build backend to use Poetry..."
	@toml set --to-array --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "build-system.requires" "[\"poetry-core>=1.0.0\"]"
	@toml set --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "build-system.build-backend" "poetry.core.masonry.api"
	@echo "==> Adding CLI entry point to [tool.poetry.scripts]..."
	@toml add_section --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "tool.poetry.scripts"
	@toml set --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "tool.poetry.scripts.$(ACRONYM_LC)" "$(SERVICE_NAME_CN)_sdk.sdk_cli:cli"
	@echo "==> Removing [project.scripts] section if it exists..."
	@sed -i '/^\[project\.scripts\]/,/^$$/d' $(PYTHON_SDK_DIR)/pyproject.toml
	@echo "==> SDK generation complete with CLI support"