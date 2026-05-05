# =============================================================================
# Global Variables and Utilities
# =============================================================================
# This file defines global variables, functions, and utilities used throughout
# the Make system. It's included first by all other .mk files.
#
# Key features:
# - Automatic version calculation from git history
# - Platform detection (Linux/macOS/Windows)
# - Port configuration management
# - Helper functions and utilities
# =============================================================================

# Set default target to 'help' so running 'make' shows available targets
.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
# Convert space-separated list to comma-separated list
# Usage: $(call to_csv,item1 item2 item3) -> "item1,item2,item3"
empty :=
space := $(empty) $(empty)
comma := ,
to_csv = $(subst $(space),$(comma),$(strip $1))

# -----------------------------------------------------------------------------
# Platform Detection
# -----------------------------------------------------------------------------
# Detect the current architecture and operating system
# Used for platform-specific commands and Docker builds
ARCH := $(shell uname -m)
OS := $(shell uname -s)

# Location of private SSH key for git+ssh dependencies during docker build
SSH_KEY ?= ~/.ssh/id_rsa 2>/dev/null

# Environment variables required for LLM services (Watson/RITS)
LLM_SVCS_ENV_VARS := RITS_API_KEY WATSONX_APIKEY WATSONX_PROJECT_ID WATSONX_URL

# -----------------------------------------------------------------------------
# Default Target Handler
# -----------------------------------------------------------------------------
# Any unimplemented target will fail here with a clear error message
.DEFAULT:
	@echo "Unimplemented target: $@"
	@false

# Create the .stamps directory for tracking build state (idempotent)
_ := $(shell mkdir -p .stamps)

# -----------------------------------------------------------------------------
# Port Configuration
# -----------------------------------------------------------------------------
# Extract the first port from SERVICE_PORTS as the main service port
# Example: SERVICE_PORTS="8000 8002" -> MAIN_SERVICE_PORT=8000
MAIN_SERVICE_PORT = $(firstword $(SERVICE_PORTS))

# Generate port environment variables file using script
# This creates .stamps/srv.env with variables like:
#   SBS_MAIN_PORT=8000
#   SBS_UI_PORT=8002
#   SBS_HOST=0.0.0.0
.stamps/srv.env: .mk/local.mk
	@if [ -n "$(ACRONYM)" ] && [ -n "$(SERVICE_PORTS)" ] && [ -n "$(SERVICE_PORT_ROLES)" ] && [ -n "$(SERVICE_HOST)" ]; then \
		$(SB_COMMON_PATH)/scripts/mk_srv_env.sh "$(ACRONYM)" "$(SERVICE_PORTS)" "$(SERVICE_PORT_ROLES)" "$(SERVICE_HOST)" 2>/dev/null || true; \
	fi

# -----------------------------------------------------------------------------
# Version Management
# -----------------------------------------------------------------------------
# Automatically calculate BUILD_VERSION from git history
# This mimics 'git describe --always --dirty' but works with our branch-based
# release strategy where each release is in a separate branch (branch-X.Y.Z)
#
# Version format examples:
#   - On release tag:           "1.2.3"
#   - After release:            "1.2.3-5-gc9b7ddd" (5 commits after 1.2.3)
#   - With uncommitted changes: "1.2.3-5-gc9b7ddd-dirty"
#   - No releases yet:          "gc9b7ddd" (just commit hash)

# Find the latest release by looking for branch-X.Y.Z branches
# Sort them by version number and take the most recent
_LATEST_RELEASE=$(shell git branch -r | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 1 | head -n 1)

# Check if there are any uncommitted changes
# Returns "-dirty" if changes exist, empty string otherwise
_DIRTY=$(shell git diff --quiet || echo "-dirty")

# Get the current commit hash (short form, 7 characters)
_CURRENT_COMMIT=$(shell git rev-parse --short=7 HEAD)

# Calculate BUILD_VERSION based on whether releases exist
ifeq ($(_LATEST_RELEASE),)
	# No releases exist yet - use just the commit hash
	# Example: "gc9b7ddd" or "gc9b7ddd-dirty"
	BUILD_VERSION="g$(_CURRENT_COMMIT)$(_DIRTY)"
else
	# Releases exist - calculate version relative to latest release
	
	# Count commits between the latest release tag and current HEAD
	# This tells us how many commits have been made since the release
	_COMMIT_COUNT=$(shell git rev-list --count $(_LATEST_RELEASE)..HEAD)
	
	ifeq ($(_COMMIT_COUNT),0)
		# We're exactly on a release tag
		# Example: "1.2.3" or "1.2.3-dirty"
		BUILD_VERSION="$(_LATEST_RELEASE)$(_DIRTY)"
	else
		# We're ahead of the release tag
		# Example: "1.2.3-5-gc9b7ddd" or "1.2.3-5-gc9b7ddd-dirty"
		BUILD_VERSION="$(_LATEST_RELEASE)-$(_COMMIT_COUNT)-g$(_CURRENT_COMMIT)$(_DIRTY)"
	endif
endif

# -----------------------------------------------------------------------------
# Platform-Specific Commands
# -----------------------------------------------------------------------------
# Detect which commands are available on this platform
ifeq ($(OS),Windows_NT)
    WHICH_CMD := where
    NULL_DEV := NUL
else
    WHICH_CMD := which
    NULL_DEV := /dev/null
endif

# Find a suitable AWK implementation (gawk preferred, awk as fallback)
ifneq (, $(shell $(WHICH_CMD) gawk 2> $(NULL_DEV)))
    AWK := gawk
else ifneq (, $(shell $(WHICH_CMD) awk 2> $(NULL_DEV)))
    AWK := awk
else
    $(error "Neither gawk nor awk found. Please install one and ensure it's in your PATH.")
endif

# Current build date/time for embedding in artifacts
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

# -----------------------------------------------------------------------------
# Help System
# -----------------------------------------------------------------------------
.PHONY: help
help: ## Display this help.
	@python $(SB_COMMON_PATH)/scripts/make-help.py $(MAKEFILE_LIST)

# Print the calculated build version (useful for debugging)
print_build_version:
	@echo $(BUILD_VERSION)

# -----------------------------------------------------------------------------
# Environment Checks
# -----------------------------------------------------------------------------
# Verify we're running in a virtual environment
# This prevents accidentally installing packages system-wide
.PHONY: check-venv
check-venv:
	@python -c "import sys, os; in_venv = ('VIRTUAL_ENV' in os.environ) or (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)); print('✅ In virtual environment' if in_venv else '❌ Not in virtual environment'); exit(0) if in_venv else exit(1)"

# Check if RITS_API_KEY is set (required for some services)
.PHONY: check_rits_key
check_rits_key:
	@if [ -z $$RITS_API_KEY ]; then echo "RITS_API_KEY is not set. It is required for the agent service"; exit 1; fi

# Check if either RITS or Watson credentials are available
# Services can use either RITS_API_KEY OR the Watson credentials
.PHONY: check-rits-watsonx-envs
check-rits-watsonx-envs:
	@missing_vars=""; \
	if [ -z "$$RITS_API_KEY" ]; then \
		if [ -z "$$WATSONX_APIKEY" ]; then missing_vars="$$missing_vars WATSONX_APIKEY"; fi; \
		if [ -z "$$WATSONX_PROJECT_ID" ]; then missing_vars="$$missing_vars WATSONX_PROJECT_ID"; fi; \
		if [ -z "$$WATSONX_URL" ]; then missing_vars="$$missing_vars WATSONX_URL"; fi; \
		if [ -n "$$missing_vars" ]; then \
			echo "Missing required environment variables: RITS_API_KEY or ($$missing_vars)"; \
			exit 1; \
		else \
			echo "All WATSONX_* variables are set. Proceeding..."; \
		fi; \
	else \
		echo "RITS_API_KEY is set. Proceeding..."; \
	fi

# -----------------------------------------------------------------------------
# SSH Agent Management
# -----------------------------------------------------------------------------
# Start or capture an existing SSH agent for git+ssh operations
# This is needed for Docker builds that access private git repositories
.PHONY: ssh-agent
ssh-agent: .stamps/ssh-agent.env

.stamps/ssh-agent.env:
	@if [ -z "$$SSH_AUTH_SOCK" ]; then \
		echo "Starting SSH agent"; \
		ssh-agent -s > .stamps/ssh-agent.env; \
	else \
		echo "Capturing running SSH agent"; \
		echo "SSH_AUTH_SOCK=$$SSH_AUTH_SOCK" > .stamps/ssh-agent.env; \
	fi 
	@. .stamps/ssh-agent.env; \
	ssh-add $(SSH_KEY);