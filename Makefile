# =============================================================================
# Skillberry Store - Root Makefile
# =============================================================================
# This is the main entry point for the Make build system.
# It manages the skillberry-common subtree and includes project configuration.
#
# Quick Start:
#   make help              - Show all available targets
#   make install-requirements - Install dependencies
#   make run               - Start the service locally
#   make docker-run        - Run with Docker
#
# For detailed documentation, see: docs/MAKE_SYSTEM.md
# =============================================================================

# Configuration for skillberry-common subtree
# This allows sharing common Make targets across multiple Skillberry projects
SB_COMMON_REPO := git@github.com:skillberry-ai/skillberry-common.git
SB_COMMON_BRANCH := main
SB_COMMON_REMOTE := skillberry-common
SB_COMMON_PATH := skillberry-common

# Ensure the skillberry-common remote exists in git
# This runs once when Make starts and adds the remote if missing
_ensure_git_remote := $(shell \
    git remote | grep -Fxq "$(SB_COMMON_REMOTE)" || { \
        echo "$(SB_COMMON_REMOTE) remote does not exist - adding it"; \
        git remote add "$(SB_COMMON_REMOTE)" "$(SB_COMMON_REPO)"; \
    })

# Include project-specific configuration (REQUIRED)
# This file must define: ASSET_NAME, ACRONYM, SERVICE_ENTRY_MODULE, etc.
include .mk/local.mk

# Include the main skillberry-common Makefile
# This brings in all shared targets (dev, docker, ci, etc.)
include $(SB_COMMON_PATH)/Makefile

# Auto-install skillberry-common if not present
# This target runs automatically if the skillberry-common Makefile is missing
$(SB_COMMON_PATH)/Makefile: 
	@echo "Adding $(SB_COMMON_REMOTE) under relative path $(SB_COMMON_PATH)"
	@git subtree add --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH)