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

##@ Development

test-e2e: ## Test end-to-end the tools service (installs sdk)
	@$(MAKE) install-requirements ODEPS=dev
	pytest src/skillberry_store/tests/e2e

lint: ## List the tools-service
	@$(MAKE) install-requirements ODEPS=dev
	black --check --diff --color src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils || \
		(echo "Lint Failed. Please run 'black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils' to fix the issues" && exit 1)

##@ Setup & teardown as a process

clean-service-data: stop
	@echo "Clean $(SERVICE_NAME) /tmp directory"
	+rm -rf /tmp/manifest
	+rm -rf /tmp/descriptions
	+rm -rf /tmp/files