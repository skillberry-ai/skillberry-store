# ============================================================================
# Skillberry Store - Root Makefile
# ============================================================================
# This is the main entry point for all Make commands.
# 
# Quick Start:
#   make help                    - Show all available commands
#   make install-requirements    - Install Python dependencies
#   make test                    - Run tests
#   make run                     - Run service locally
#   make docker-build            - Build Docker image
#
# Documentation: See docs/MAKE_SYSTEM.md for detailed information
# ============================================================================

# ----------------------------------------------------------------------------
# Skillberry Common System Integration
# ----------------------------------------------------------------------------
# The skillberry-common directory contains shared Make logic used across
# multiple Skillberry projects. It's managed as a Git subtree.

SB_COMMON_REPO := git@github.com:skillberry-ai/skillberry-common.git
SB_COMMON_BRANCH := main
SB_COMMON_REMOTE := skillberry-common
SB_COMMON_PATH := skillberry-common

# Ensure the skillberry-common remote exists
_ensure_git_remote := $(shell \
    git remote | grep -Fxq "$(SB_COMMON_REMOTE)" || { \
        echo "$(SB_COMMON_REMOTE) remote does not exist - adding it"; \
        git remote add "$(SB_COMMON_REMOTE)" "$(SB_COMMON_REPO)"; \
    })

# ----------------------------------------------------------------------------
# Include Configuration and Common System
# ----------------------------------------------------------------------------
# Load order matters:
# 1. local.mk - Project-specific configuration (REQUIRED)
# 2. skillberry-common/Makefile - Shared system (provides most targets)
# 3. Project-specific .mk files can override common targets

include .mk/local.mk
include $(SB_COMMON_PATH)/Makefile

# ----------------------------------------------------------------------------
# Auto-install Skillberry Common (if missing)
# ----------------------------------------------------------------------------
# If the skillberry-common Makefile doesn't exist, automatically fetch it
# from the repository using git subtree.

$(SB_COMMON_PATH)/Makefile: 
	@echo "============================================================"
	@echo "Installing skillberry-common system..."
	@echo "============================================================"
	@echo "Adding $(SB_COMMON_REMOTE) under relative path $(SB_COMMON_PATH)"
	@git subtree add --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH)
	@echo "✓ Skillberry-common installed successfully"
	@echo ""