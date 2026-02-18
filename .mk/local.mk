# ----------- MANDATORY IDENTIFIERS ------------------
# Names: No spaces, letter start, letters, digits, hyphen, underscore
# Python path names: also no hyphen
# Make sure NO TRAILING WHITE SPACES after values! No quotes or double-quotes!
ASSET_NAME := skillberry-store
ACRONYM := SBS
DESC_NAME := Skillberry Store service
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py
# Set to 1 if this asset is using LLM services - watsonx or RITS
USE_LLM_SVCS := 0
# Set these two below even if your asset is not a service - it allows execution control 
SERVICE_ENTRY_MODULE := skillberry_store.main
SERVICE_NAME := $(ASSET_NAME)
# If this asset is an actual network service, define these service settings as well
SERVICE_PORTS := 8000 8002
SERVICE_PORT_ROLES := MAIN UI
SERVICE_HOST := 0.0.0.0
SERVICE_HAS_SDK := 1
# ----------------------------------------------------

include .mk/dev.mk
include .mk/process.mk
#include .mk/docker.mk
#include .mk/ci.mk
