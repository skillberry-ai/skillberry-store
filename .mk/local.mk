# =============================================================================
# Project Configuration - Skillberry Store
# =============================================================================
# This file contains all project-specific settings required by the Make system.
# These values are used throughout the build, deployment, and CI/CD processes.
#
# IMPORTANT: 
# - No trailing whitespace after values
# - No quotes around values
# - Names: letters, digits, hyphen, underscore only (no spaces)
# - Python module names: no hyphens (use underscores)
# =============================================================================

# -----------------------------------------------------------------------------
# Project Identity
# -----------------------------------------------------------------------------
# ASSET_NAME: The project's identifier (used for Docker images, directories)
# Format: lowercase, hyphens allowed, no spaces
ASSET_NAME := skillberry-store

# ACRONYM: Short uppercase identifier (used for environment variables, CLI)
# Format: uppercase letters only
ACRONYM := SBS

# DESC_NAME: Human-readable project description
DESC_NAME := Skillberry Store service

# -----------------------------------------------------------------------------
# Version Management
# -----------------------------------------------------------------------------
# VERSION_LOCATION: Path to file where git version is written
# This file is auto-generated and should be in .gitignore
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py

# -----------------------------------------------------------------------------
# LLM Services Configuration
# -----------------------------------------------------------------------------
# USE_LLM_SVCS: Set to 1 if this service uses Watson/RITS LLM services
# When enabled, the system will check for required environment variables:
# - RITS_API_KEY or (WATSONX_APIKEY, WATSONX_PROJECT_ID, WATSONX_URL)
USE_LLM_SVCS := 0

# -----------------------------------------------------------------------------
# Service Configuration
# -----------------------------------------------------------------------------
# SERVICE_ENTRY_MODULE: Python module to execute when starting the service
# Format: module.path (e.g., package.subpackage.main)
SERVICE_ENTRY_MODULE := skillberry_store.main

# SERVICE_NAME: Name used for process management and Docker containers
# Typically same as ASSET_NAME
SERVICE_NAME := $(ASSET_NAME)

# SERVICE_PORTS: Space-separated list of ports the service uses
# First port is the main API port, subsequent ports are for additional services
SERVICE_PORTS := 8000 8002

# SERVICE_PORT_ROLES: Space-separated role names for each port
# Must match the number of ports in SERVICE_PORTS
# Used to generate environment variables like SBS_MAIN_PORT, SBS_UI_PORT
SERVICE_PORT_ROLES := MAIN UI

# SERVICE_HOST: IP address the service binds to
# 0.0.0.0 = all interfaces, 127.0.0.1 = localhost only
SERVICE_HOST := 0.0.0.0

# SERVICE_HAS_SDK: Set to 1 if this service generates a Python SDK
# When enabled, 'make update-sdk' will generate SDK from OpenAPI spec
SERVICE_HAS_SDK := 1

# -----------------------------------------------------------------------------
# Include Additional Make Files
# -----------------------------------------------------------------------------
# These files contain project-specific targets that extend the common system

# Development targets (testing, linting, etc.)
include .mk/dev.mk

# Process management targets (service-specific cleanup, etc.)
include .mk/process.mk

# Optional includes (uncomment if needed):
# include .mk/docker.mk    # Project-specific Docker customizations
# include .mk/ci.mk        # Project-specific CI/CD targets