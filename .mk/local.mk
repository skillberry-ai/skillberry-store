# ============================================================================
# Project Configuration - Skillberry Store
# ============================================================================
# This file contains all project-specific settings for the Make system.
# Edit these values to match your project's requirements.
#
# Documentation: See docs/MAKE_SYSTEM.md for detailed explanations
# ============================================================================

# ----------------------------------------------------------------------------
# MANDATORY: Project Identity
# ----------------------------------------------------------------------------
# These values identify your project and are used throughout the build system.
#
# Naming Rules:
#   - No spaces allowed
#   - Start with a letter
#   - Use letters, digits, hyphens, and underscores only
#   - For Python paths: no hyphens (use underscores instead)
#   - NO TRAILING WHITESPACE after values!
#   - NO quotes or double-quotes!

# Project name (used for Docker images, directories, etc.)
# Example: skillberry-store, my-service, data-processor
ASSET_NAME := skillberry-store

# Short acronym (2-4 letters, used for CLI tools and environment variables)
# Example: SBS, API, DB
ACRONYM := SBS

# Human-readable description (used in logs and documentation)
DESC_NAME := Skillberry Store service

# Path to file where Git version will be written (relative to project root)
# This file is auto-generated and should be in .gitignore
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py

# ----------------------------------------------------------------------------
# MANDATORY: Service Configuration
# ----------------------------------------------------------------------------
# These settings control how your service runs.

# Python module to execute when starting the service
# Format: package.module (no .py extension)
# Example: myapp.main, services.api.server
SERVICE_ENTRY_MODULE := skillberry_store.main

# Service name (usually same as ASSET_NAME, used for process management)
SERVICE_NAME := $(ASSET_NAME)

# ----------------------------------------------------------------------------
# MANDATORY: Network Configuration
# ----------------------------------------------------------------------------
# Define the ports your service uses and their purposes.

# Space-separated list of port numbers
# First port is always the main service port
# Example: 8000 8002 9090
SERVICE_PORTS := 8000 8002

# Space-separated list of role names (one per port, in same order)
# These become environment variables: {ACRONYM}_{ROLE}_PORT
# Example: MAIN UI METRICS → SBS_MAIN_PORT=8000, SBS_UI_PORT=8002
SERVICE_PORT_ROLES := MAIN UI

# Host address to bind to
# Use 0.0.0.0 to accept connections from any network interface
# Use 127.0.0.1 to accept only local connections
SERVICE_HOST := 0.0.0.0

# ----------------------------------------------------------------------------
# OPTIONAL: Feature Flags
# ----------------------------------------------------------------------------

# Set to 1 if this service uses LLM services (WatsonX or RITS)
# When enabled, requires environment variables:
#   - RITS_API_KEY, or
#   - WATSONX_APIKEY, WATSONX_PROJECT_ID, WATSONX_URL
USE_LLM_SVCS := 0

# Set to 1 if this service generates a client SDK
# When enabled, 'make release' will automatically update the SDK
SERVICE_HAS_SDK := 1

# ----------------------------------------------------------------------------
# Include Project-Specific Make Files
# ----------------------------------------------------------------------------
# These files contain additional targets specific to this project.
# They can override or extend targets from skillberry-common.

include .mk/dev.mk       # Development tasks (testing, linting, etc.)
include .mk/process.mk   # Service lifecycle management (start, stop, clean)

# Uncomment these if you need them:
# include .mk/docker.mk  # Custom Docker configurations
# include .mk/ci.mk      # Custom CI/CD tasks