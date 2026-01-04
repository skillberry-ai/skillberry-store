# ----------- MANDATORY IDENTIFIERS ------------------
SERVICE_NAME = skillberry-store
SERVICE_ENTRY_MODULE = blueberry_tools_service.main
VERSION_LOCATION = blueberry_tools_service/fast_api/git_version.py
# ----------------------------------------------------

export BTS_PORT := $(or $(shell echo $$BTS_PORT), 8000) 
export BTS_HOST := $(or $(shell echo $$BTS_HOST), 0.0.0.0)

SERVICE_DOCKER_SETUP := "-e BTS_HOST=$(strip $(BTS_HOST)) -e BTS_PORT=$(strip $(BTS_PORT))"

include dev.mk
include process.mk
#include docker.mk
#include ci.mk
