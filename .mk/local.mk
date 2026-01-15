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

export BTS_PORT := $(or $(shell echo $$BTS_PORT), 8000) 
export BTS_HOST := $(or $(shell echo $$BTS_HOST), 0.0.0.0)

SERVICE_DOCKER_SETUP := "-e BTS_HOST=$(strip $(BTS_HOST)) -e BTS_PORT=$(strip $(BTS_PORT))"

include .mk/dev.mk
include .mk/process.mk
#include .mk/docker.mk
#include .mk/ci.mk
