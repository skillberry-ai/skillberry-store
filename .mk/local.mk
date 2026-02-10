# ----------- MANDATORY IDENTIFIERS ------------------
# Names: No spaces, letter start, letters, digits, hyphen, underscore
# Python path names: also no hyphen
ASSET_NAME := skillberry-store
ACRONYM := SBS
DESC_NAME := "Skillberry Store service"
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py
# If this project is a service, define these service settings as well
SERVICE_NAME := $(ASSET_NAME)
SERVICE_PORTS := 8000 8001 8002
SERVICE_PORT_ROLES := MAIN CONFIG UI
SERVICE_HOST := 0.0.0.0 
SERVICE_ENTRY_MODULE := skillberry_store.main
SERVICE_HAS_SDK := 1
# ----------------------------------------------------

include .mk/dev.mk
include .mk/process.mk
#include .mk/docker.mk
#include .mk/ci.mk
