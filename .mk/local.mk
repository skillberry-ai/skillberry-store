# ============================================================================
# Project Configuration
# ============================================================================
# This file contains all project-specific settings for the Skillberry Store.
# Modify these values to match your project's requirements.
#
# For detailed documentation, see: docs/MAKE_SYSTEM.md
# ============================================================================

# ============================================================================
# Project Identity
# ============================================================================
# ASSET_NAME: The name of your project/asset
#   - Used for Docker image naming, logging, and identification
#   - Format: lowercase, hyphens allowed, no spaces
#   - Example: skillberry-store, my-service, data-processor
ASSET_NAME := skillberry-store

# ACRONYM: Short abbreviation for your project
#   - Used for environment variable prefixes (e.g., SBS_MAIN_PORT)
#   - Format: uppercase letters only, typically 2-4 characters
#   - Example: SBS (Skillberry Store), API, DB
ACRONYM := SBS

# DESC_NAME: Human-readable description of your project
#   - Used in logs, documentation, and user-facing messages
#   - Format: any readable text
DESC_NAME := Skillberry Store service

# ============================================================================
# Version Management
# ============================================================================
# VERSION_LOCATION: Path to the file where git version is written
#   - This file is auto-generated and should not be manually edited
#   - The version format is: 0.5.3 or 0.5.3-5-gc9b7ddd or 0.5.3-dirty
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py

# ============================================================================
# LLM Services Configuration (Optional)
# ============================================================================
# USE_LLM_SVCS: Set to 1 if your service uses LLM services (watsonx or RITS)
#   - 0: No LLM services (default)
#   - 1: Requires RITS_API_KEY or WATSONX_* environment variables
#
# If set to 1, you must provide one of:
#   - RITS_API_KEY environment variable, OR
#   - All three: WATSONX_APIKEY, WATSONX_PROJECT_ID, WATSONX_URL
USE_LLM_SVCS := 0

# ============================================================================
# Service Configuration
# ============================================================================
# SERVICE_ENTRY_MODULE: Python module to run when starting the service
#   - Format: python.module.path (use dots, not slashes)
#   - This is passed to: python -m <SERVICE_ENTRY_MODULE>
#   - Example: skillberry_store.main, myapp.server, api.app
SERVICE_ENTRY_MODULE := skillberry_store.main

# SERVICE_NAME: Name used for process management and Docker containers
#   - Usually same as ASSET_NAME
#   - Used for PID files, log files, and container names
SERVICE_NAME := $(ASSET_NAME)

# ============================================================================
# Network Configuration
# ============================================================================
# SERVICE_PORTS: Space-separated list of ports your service uses
#   - First port is considered the "main" service port
#   - Additional ports are for auxiliary services (UI, metrics, etc.)
#   - Example: "8000" (single port) or "8000 8002" (main + UI)
SERVICE_PORTS := 8000 8002

# SERVICE_PORT_ROLES: Space-separated list of port roles (must match SERVICE_PORTS count)
#   - Describes what each port is used for
#   - Used to generate environment variables like: SBS_MAIN_PORT, SBS_UI_PORT
#   - Example: "MAIN" or "MAIN UI" or "API METRICS ADMIN"
SERVICE_PORT_ROLES := MAIN UI

# SERVICE_HOST: Host address to bind the service to
#   - 0.0.0.0: Listen on all network interfaces (typical for services)
#   - localhost or 127.0.0.1: Listen only on local machine
#   - Specific IP: Listen on a specific network interface
SERVICE_HOST := 0.0.0.0

# ============================================================================
# SDK Configuration
# ============================================================================
# SERVICE_HAS_SDK: Set to 1 if this service has a client SDK
#   - 0: No SDK (default)
#   - 1: Has SDK - enables SDK generation and update targets
#
# If set to 1, the following targets become available:
#   - make generate-sdk: Generate SDK from OpenAPI spec
#   - make update-sdk: Update SDK after API changes
SERVICE_HAS_SDK := 1

# ============================================================================
# Note on Additional Configuration Files
# ============================================================================
# Project-specific targets are defined in:
#   - .mk/dev.mk: Development-specific targets (tests, linting, etc.)
#   - .mk/process.mk: Service lifecycle targets (custom cleanup, initialization, etc.)
#
# These files are automatically included by the main Makefile.
# Do not include them here to avoid duplicate definitions.

# ============================================================================
# Configuration Notes
# ============================================================================
# 1. All paths should be relative to the project root
# 2. No trailing whitespace after values
# 3. No quotes around values (unless they contain spaces)
# 4. Use := for immediate assignment (recommended)
# 5. Use ?= for default values that can be overridden
# 6. Use = for recursive expansion (use sparingly)
#
# Common Mistakes to Avoid:
#   ✗ ASSET_NAME = "my-service"  (don't use quotes)
#   ✓ ASSET_NAME := my-service
#
#   ✗ SERVICE_PORTS := 8000,8002  (don't use commas)
#   ✓ SERVICE_PORTS := 8000 8002
#
#   ✗ SERVICE_HOST := 0.0.0.0     (trailing space)
#   ✓ SERVICE_HOST := 0.0.0.0
# ============================================================================