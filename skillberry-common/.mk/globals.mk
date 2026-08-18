.DEFAULT_GOAL := help

# function for converting space-separated list to comma-separated list
empty :=
space := $(empty) $(empty)
comma := ,
to_csv = $(subst $(space),$(comma),$(strip $1))


ARCH := $(shell uname -m)
OS := $(shell uname -s)

# Location of private SSH key for git+ssh dependencies, e.g., during docker build
SSH_KEY ?= $(HOME)/.ssh/id_rsa

LLM_SVCS_ENV_VARS := RITS_API_KEY WATSONX_APIKEY WATSONX_PROJECT_ID WATSONX_URL

.DEFAULT:	# Any unimplemented target or dependency will fail here
	@echo "Unimplemented target: $@"
	@false

# Create the .stamps directory (idempotent)
_ := $(shell mkdir -p .stamps)

# Port setup
#
# The first port in SERVICE_PORTS is the main service port.
# The second port etc are optional, defined specifically for each service
MAIN_SERVICE_PORT = $(firstword $(SERVICE_PORTS))

# Generate port environment variables file using script
.stamps/srv.env: .mk/local.mk
	@if [ -n "$(ACRONYM)" ] && [ -n "$(SERVICE_PORTS)" ] && [ -n "$(SERVICE_PORT_ROLES)" ] && [ -n "$(SERVICE_HOST)" ]; then \
		$(SB_COMMON_PATH)/scripts/mk_srv_env.sh "$(ACRONYM)" "$(SERVICE_PORTS)" "$(SERVICE_PORT_ROLES)" "$(SERVICE_HOST)" 2>/dev/null || true; \
	fi

# BUILD_VERSION: single label that identifies the current repository state.
#
# Computed by scripts/git-version.sh, which:
#   - matches `git describe --always --dirty` conventions:
#       clean at release commit:            <release>            (e.g. 0.5.3)
#       N commits past latest release:      <release>-<N>-g<sha> (e.g. 0.5.3-5-gc9b7ddd)
#       no release yet:                     g<sha>               (e.g. gc9b7ddd)
#   - detects dirty state via `git status --porcelain` (staged + unstaged +
#     untracked non-ignored) and appends `-dirty-<7hex>`, where the hex is a
#     fingerprint of the actual dirty content, so different dirty states get
#     different labels (concept 1 of docs/design/build_concepts.md).
BUILD_VERSION := $(shell $(SB_COMMON_PATH)/scripts/git-version.sh)

# Platform-specific variables
ifeq ($(OS),Windows_NT)
    WHICH_CMD := where
    NULL_DEV := NUL
else
    WHICH_CMD := which
    NULL_DEV := /dev/null
endif

# Try to find a suitable AWK implementation
ifneq (, $(shell $(WHICH_CMD) gawk 2> $(NULL_DEV)))
    AWK := gawk
else ifneq (, $(shell $(WHICH_CMD) awk 2> $(NULL_DEV)))
    AWK := awk
else
    $(error "Neither gawk nor awk found. Please install one and ensure it's in your PATH.")
endif

BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

.PHONY: help
help: ## Display this help.
	@python $(SB_COMMON_PATH)/scripts/make-help.py $(MAKEFILE_LIST)

print_build_version:
	@echo $(BUILD_VERSION)

.PHONY: check-venv
check-venv:
	@python -c "import sys, os; in_venv = ('VIRTUAL_ENV' in os.environ) or (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)); print('✅ In virtual environment' if in_venv else '❌ Not in virtual environment'); exit(0) if in_venv else exit(1)"

.PHONY: check_rits_key
check_rits_key:
	@if [ -z $$RITS_API_KEY ]; then echo "RITS_API_KEY is not set. It is required for the agent service"; exit 1; fi

.PHONY: check-rits-watsonx-envs
check-rits-watsonx-envs:
	@missing_vars=""; \
	if [ -z "$$RITS_API_KEY" ]; then \
		if [ -z "$$WATSONX_APIKEY" ]; then missing_vars="$$missing_vars WATSONX_APIKEY"; fi; \
		if [ -z "$$WATSONX_PROJECT_ID" ]; then missing_vars="$$missing_vars WATSONX_PROJECT_ID"; fi; \
		if [ -z "$$WATSONX_URL" ]; then missing_vars="$$missing_vars WATSONX_URL"; fi; \
		if [ -n "$$missing_vars" ]; then \
			echo "Missing required environment variables: RITS_API_KEY or ($$missing_vars)"; \
			exit 1; \
		else \
			echo "All WATSONX_* variables are set. Proceeding..."; \
		fi; \
	else \
		echo "RITS_API_KEY is set. Proceeding..."; \
	fi

.PHONY: ssh-agent
ssh-agent: .stamps/ssh-agent.env

.stamps/ssh-agent.env:
	@if [ -z "$$SSH_AUTH_SOCK" ]; then \
		echo "Starting SSH agent"; \
		ssh-agent -s > .stamps/ssh-agent.env; \
	else \
		echo "Capturing running SSH agent"; \
		echo "SSH_AUTH_SOCK=$$SSH_AUTH_SOCK" > .stamps/ssh-agent.env; \
	fi 
	@. .stamps/ssh-agent.env; \
	ssh-add $(SSH_KEY); 


