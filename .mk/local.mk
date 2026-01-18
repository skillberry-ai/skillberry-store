# ----------- MANDATORY IDENTIFIERS ------------------
# Names: No spaces, letter start, letters, digits, hyphen, underscore
# Python path names: also no hyphen
ASSET_NAME := skillberry-store
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py
# If this project is a service, define these service settings as well
SERVICE_NAME := $(ASSET_NAME)
SERVICE_PORT := 8000 
SERVICE_ENTRY_MODULE := skillberry_store.main
# ----------------------------------------------------

export SBS_PORT := $(or $(shell echo $$SBS_PORT), 8000) 
export SBS_HOST := $(or $(shell echo $$SBS_HOST), 0.0.0.0)

SERVICE_DOCKER_SETUP := "-e SBS_HOST=$(strip $(SBS_HOST)) -e SBS_PORT=$(strip $(SBS_PORT))"

include .mk/dev.mk
include .mk/process.mk
#include .mk/docker.mk
#include .mk/ci.mk
