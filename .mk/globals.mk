.DEFAULT_GOAL ?= help

ARCH := $(shell uname -m)
OS := $(shell uname -s)

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

# Define ports based on ACRONYM, SERVICE_PORTS and SERVICE_PORT_ROLES e.g., "SBS_PORT","SBM_CONFIG_PORT" etc

# --- Validate lengths match ---
_ports_n := $(words $(SERVICE_PORTS))
_roles_n := $(words $(SERVICE_PORT_ROLES))
ifneq ($(_ports_n),$(_roles_n))
  $(error SERVICE_PORTS has $(_ports_n) items; SERVICE_PORT_ROLES has $(_roles_n). They must match.)
endif

# --- Zip roles and ports: "MAIN:8000 CONFIG:8001 UI:8002" ---
_pairs := $(join $(addsuffix :, $(SERVICE_PORT_ROLES)),$(SERVICE_PORTS))

# --- Build the export lines (MAIN omits the role in the var name) ---
_export_lines := \
$(foreach _p,$(_pairs), \
  $(if $(filter MAIN,$(firstword $(subst :, ,$(_p)))), \
    export $(ACRONYM)_PORT = $(word 2,$(subst :, ,$(_p))), \
    export $(ACRONYM)_$(subst -,_,$(firstword $(subst :, ,$(_p))))_PORT = $(word 2,$(subst :, ,$(_p))) ) \
)

# --- Materialize the dynamic exports ---
$(eval $(_export_lines))

# ---------- Optional: a helper target to show what was defined ----------
.PHONY: show-ports
show-ports:
    @echo "$(ACRONYM)_PORT=$($(ACRONYM)_PORT)"
    @$(foreach r,$(filter-out MAIN,$(SERVICE_PORT_ROLES)), \
        echo "$(ACRONYM)_$(subst -,_,$(r))_PORT=$($(ACRONYM)_$(subst -,_,$(r))_PORT)";)



# Set BUILD_VERSION variable
#
# In SkillBerry every tag/release is created in a separate branch (to have dedicated toml with
# proper @ to sdk). So we implement our logic to maintain git format for 'git describe --always --dirty'
# - i.e. 0.5.3 or 0.5.3-5-gc9b7ddd or 0.5.3-5-gc9b7ddd-dirty

_LATEST_RELEASE=$(shell git branch -r | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 1 | head -n 1)

#
# _LATEST_RELEASE is the actual tag e.g. 0.5.3
#
ifeq ($(_LATEST_RELEASE),)
	#
	# Latest release does not exist
	#

	_CURRENT_COMMIT=$(shell git rev-parse --short=7 HEAD)
	# sets with "dirty" if there are uncommitted changes
	_DIRTY=$(shell git diff --quiet || echo "-dirty")
	# e.g. gc9b7ddd, gc9b7ddd-dirty
	BUILD_VERSION="g$(_CURRENT_COMMIT)$(_DIRTY)"
else
	# Find the common ancestor (branch point)
	# TODO: confirm _BASE_COMMIT not needed and remove 
	# _BASE_COMMIT=$(shell git merge-base origin/main origin/branch-$(_LATEST_RELEASE))

	#
	# Count commits in main after the branch point
	# tag is git global - can be safely used
	#
	_COMMIT_COUNT=$(shell git rev-list --count $(_LATEST_RELEASE)..HEAD)

	_CURRENT_COMMIT=$(shell git rev-parse --short=7 HEAD)

	_DIRTY=$(shell git diff --quiet || echo "-dirty")

	ifeq ($(_COMMIT_COUNT),0)
		# e.g. 0.4
		BUILD_VERSION="$(_LATEST_RELEASE)$(_DIRTY)"
	else
		# e.g. 0.4-70-gc9b7ddd
		BUILD_VERSION="$(_LATEST_RELEASE)-$(_COMMIT_COUNT)-g$(_CURRENT_COMMIT)$(_DIRTY)"
	endif
endif

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

ifeq ($(ARCH), arm64)
	DOCKER_FILE := Dockerfile-$(ARCH)
endif

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


