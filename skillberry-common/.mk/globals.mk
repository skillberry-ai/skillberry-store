.DEFAULT_GOAL := help

# Deploy-only mode. When TRUE, dev-time work (dependency install, UI build,
# git plumbing, git-based version derivation) is bypassed on the `run` path
# and inside parse-time hooks. User-facing (## commented) targets still work
# fully when invoked directly, regardless of this flag.
DEPLOY_ONLY ?= FALSE

# function for converting space-separated list to comma-separated list
empty :=
space := $(empty) $(empty)
comma := ,
to_csv = $(subst $(space),$(comma),$(strip $1))


ARCH := $(shell uname -m)
OS := $(shell uname -s)

# Location of private SSH key for git+ssh dependencies, e.g., during docker build
SSH_KEY ?= ~/.ssh/id_rsa 2>/dev/null

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

# Set BUILD_VERSION variable
#
# In SkillBerry every tag/release is created in a separate branch (to have dedicated toml with
# proper @ to sdk). So we implement our logic to maintain git format for 'git describe --always --dirty'
# - i.e. 0.5.3 or 0.5.3-5-gc9b7ddd or 0.5.3-5-gc9b7ddd-dirty

ifeq ($(DEPLOY_ONLY),TRUE)
# Deploy-only: skip git-based derivation and honor a pre-baked BUILD_VERSION
# from the environment (e.g., the Docker image build args).
BUILD_VERSION ?= "unknown"
else
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
	@# The redirect above creates the file even when ssh-agent fails to start
	@# (e.g. "too long for Unix domain socket"), and make would then treat this
	@# stamp as up to date forever while docker-build sources an empty file and
	@# passes `--ssh default=` to buildx. Fail here, where the cause is still
	@# visible, and drop the unusable stamp so the next run retries.
	@if ! grep -q SSH_AUTH_SOCK .stamps/ssh-agent.env; then \
		echo "ERROR: could not obtain an SSH agent socket - see the error above."; \
		rm -f .stamps/ssh-agent.env; \
		exit 1; \
	fi
	@# Adding a key is best-effort. A CI runner (and any checkout that builds
	@# only public dependencies) has no ~/.ssh/id_rsa, and ssh-add then exits 1
	@# with its message swallowed by the redirect baked into $(SSH_KEY) - which
	@# is how every ci-push run died at this step, before docker-build, with no
	@# diagnostic at all. Docker still gets the agent socket from this stamp via
	@# `--ssh default=$$SSH_AUTH_SOCK`; a keyless agent simply resolves no
	@# private git dependency over SSH.
	@. .stamps/ssh-agent.env; \
	if ssh-add $(SSH_KEY); then \
		echo "SSH key added to the agent"; \
	else \
		echo "NOTE: no SSH key added to the agent (tried $(SSH_KEY)) - continuing."; \
		echo "      Builds that fetch private git dependencies over SSH will fail."; \
	fi


