##@ Development

# List here all supported Python version specs (one or more separated by space). 
# Spec options: v1 v1.v2 v1.v2.v3
# Can add "+" to specify minimal version
# Example: 3.13+ 3.12.9 3.11.5+
SUPPORTED_PYTHON_VERSIONS := 3.11 3.12.10

# Service name in lowercase
SERVICE_NAME_LC = $(shell printf "%s" "$(SERVICE_NAME)" | tr '[:upper:]' '[:lower:]')
# Service name in code notation - lowercase + replace hyphen->underscore
SERVICE_NAME_CN ?= $(shell printf "%s" "$(SERVICE_NAME_LC)" | tr '-' '_')

ACRONYM_LC ?= $(shell echo $(ACRONYM) | tr '[:upper:]' '[:lower:]')

RESTISH_CONFIG_APIS ?= $(HOME)/.config/restish/apis.json

OPEN_API_SPEC_URL ?= http://$(SERVICE_HOST):$(MAIN_SERVICE_PORT)

export SERVICE_HAS_SDK ?= 0

# List your subtree roots
CODE_SUBTREES := src .mk $(SB_COMMON_PATH)/.mk $(SB_COMMON_PATH)/scripts

# One common filter for all
CODE_FILTER := \( -name '*.py' -o -name 'Makefile' -o -name '*.mk' -o -name '*.sh' \)

# Expand to the union of files across all subtrees
CODE_FILES := $(foreach T,$(CODE_SUBTREES), \
  $(shell find $(T) -type f $(CODE_FILTER) -print))

CODE_FILES := $(CODE_FILES) pyproject.toml Makefile Dockerfile

# This stamp file checks for code changes
.stamps/code-scan: $(CODE_FILES) 
	@echo "Detected code changed in: $(CODE_SUBTREES)"
	@touch .stamps/code-scan

git-hooks-setup:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    echo "Setting up Git hooks..."; \
	    git config core.hooksPath .githooks; \
	    chmod +x .githooks/*; \
	else \
	    echo "Skipping git-hooks-setup: not inside a Git repository."; \
	fi

.PHONY: show-srv-env
show-srv-env: .stamps/srv.env	## Show service env (ports, host)
	@cat .stamps/srv.env

test: install-requirements ## Test the tools-service
	pytest

check-git-clean:
	@changes="$$(git status --porcelain)"; \
	if [ -n "$$changes" ]; then \
	  echo "! You have uncommitted changes. Please commit, stash or clean them before releasing."; \
	  echo "=== Changes ==="; \
	  echo "$$changes"; \
	  exit 1; \
	fi

check-git-main:
	@if [ "$(shell git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
		echo "! You must be on the main branch to run this command"; \
		exit 1; \
	fi

.PHONY: install-requirements verify-venv
install-requirements: update-git-version git-hooks-setup verify-venv .stamps/install-requirements-$(ODEPS) ## Install dependencies. For opt. deps: make install-requirements ODEPS=dev,vllm
	@true

verify-venv:
	@$(SB_COMMON_PATH)/scripts/check_venv.sh $(SUPPORTED_PYTHON_VERSIONS) || exit 1
	@python -m pip install uv

# Need to actually install only when pyproject.toml changes
.stamps/install-requirements-$(ODEPS): pyproject.toml .venv
	@ODEPS="$(ODEPS)"; \
	if [ -z "$$ODEPS" ]; then \
		uv pip install -e .; \
	else \
		uv pip install -e .[$(ODEPS)]; \
	fi
	@touch .stamps/install-requirements-$(ODEPS)


# Will actually modify the file in $(VERSIOIN_LOCATION) only if it does not exist or has different content

.PHONY: update-git-version
update-git-version:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    NEW_CONTENT="__git_version__ = \"$(BUILD_VERSION)\""; \
	    if [ ! -f "$(VERSION_LOCATION)" ]; then \
	        echo "Creating git version file at $(VERSION_LOCATION)"; \
	        echo "$$NEW_CONTENT" > $(VERSION_LOCATION); \
	    else \
	        CURRENT_CONTENT=$$(cat $(VERSION_LOCATION) 2>/dev/null || echo ""); \
	        if [ "$$CURRENT_CONTENT" != "$$NEW_CONTENT" ]; then \
	            echo "Updating git version in $(VERSION_LOCATION)"; \
	            echo "$$NEW_CONTENT" > $(VERSION_LOCATION); \
	        else \
	            echo "Git version in $(VERSION_LOCATION) is already up to date"; \
	        fi; \
	    fi; \
	else \
	    echo "Skipping update-git-version: not inside a Git repository."; \
	fi

release: check-git-main check-git-clean install-requirements  ## Release a new version
	@if [ -z "$(RELEASE_VERSION)" ]; then \
		echo "++++++++++++++++++++++++++++++++++++++++++++"; \
  		echo "RELEASE_VERSION is not set. It is required for the release"; \
  		echo "Please set RELEASE_VERSION and use 'RELEASE_VERSION=<version> make release' "; \
		echo "++++++++++++++++++++++++++++++++++++++++++++"; \
	exit 1; fi

	@command -v sed >/dev/null 2>&1 || { echo "❌ 'sed' is not installed. Aborting."; exit 1; }
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Creating release with version: $(RELEASE_VERSION)"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@sleep 10
	@echo "===> Generating git tag $(RELEASE_VERSION) and creating GitHub release"
	@git checkout -b branch-$(RELEASE_VERSION)
	@echo "===> Generated release branch $(RELEASE_VERSION)"
	@git tag -a $(RELEASE_VERSION) -m "Release $(RELEASE_VERSION)" 
	@git push origin $(RELEASE_VERSION)

	#
	# Important: change to main so that later invocation of "update-git-version" properly works,
	# Note: update-git-version is called on different contexts later in this flow
	#
	@git checkout main

	#
	# The following block calls either to "basic" gh release command or an "explicit" one:
	# 
	# If no previous release exists then "basic" is called
	# If a previous release exists then "explicit" using commit range is called
	#

	@REL_PREV_RELEASE=$$(git branch -r | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 2 | head -n 1); \
	if [ -z "$$REL_PREV_RELEASE" ] || [ "$$REL_PREV_RELEASE" = "$(RELEASE_VERSION)" ]; then \
		echo "No previous release found. Creating release with generated notes..."; \
		gh release create $(RELEASE_VERSION) --generate-notes; \
	else \
		echo "Previous release found: $$REL_PREV_RELEASE"; \
		REL_CURRENT_COMMIT=$$(git rev-parse --short=7 HEAD); \
		REL_PREV_COMMIT=$$(git merge-base origin/main origin/branch-$$REL_PREV_RELEASE); \
		echo "Creating release from $$REL_PREV_COMMIT to $$REL_CURRENT_COMMIT..."; \
		gh release create $(RELEASE_VERSION) --title "$(RELEASE_VERSION)" --notes "$$(git log --pretty=format:'- %s by %an' $$REL_PREV_COMMIT..$$REL_CURRENT_COMMIT)"; \
	fi

	#
	# Important: change back to release branch so that docker image is built with customized
	# toml/requirement files
	#
	@git checkout branch-$(RELEASE_VERSION)

	@echo "===> Building and pushing new docker image"
	@make docker-push
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Release $(RELEASE_VERSION) created successfully"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"


update-sdk: ## Update the SDK, if needed
	@if [ "$$SERVICE_HAS_SDK" = "1" ]; then \
		rm -rf /tmp/skillberry-sdk || true; \
		echo "==> Updating SDK..."; \
		make docker-run; \
		timeout 120 bash -c 'until curl -sf $(OPEN_API_SPEC_URL)/docs > /dev/null; do echo "Waiting for $(DESC_NAME)..."; sleep 5; done'; \
		echo "$(DESC_NAME) started (using docker)"; \
		make generate-sdk && \
		echo "SDK updated successfully" && \
		git add . && \
		if git diff --cached --quiet; then \
			echo "!!! No updates to commit !!!"; \
		else \
			echo "!!! Updates detected, committing... !!!"; \
			git commit -m "Update $(SERVICE_NAME_CN)_sdk $$(date '+%Y-%m-%d %H:%M:%S')"; \
		fi; \
		make docker-stop; \
		echo "$(DESC_NAME) stopped"; \
		echo "==> SDK update completed successfully"; \
	else \
		echo "Service has no SDK, skipping"; \
	fi

PYTHON_SDK_DIR = client/python/$(SERVICE_NAME_CN)_sdk

generate-sdk: install-requirements # Generate SDK
	@mkdir -p $(PYTHON_SDK_DIR)
	@rm -fr $(PYTHON_SDK_DIR)/*
	@openapi-generator-cli generate -i $(OPEN_API_SPEC_URL)/openapi.json \
		-g python \
		-o $(PYTHON_SDK_DIR) \
		--package-name $(SERVICE_NAME_CN)_sdk
	@echo "==> Adding CLI module to SDK..."
	@sed -e 's|{{API_NAME}}|$(ACRONYM_LC)|g' \
	     -e 's|{{API_URL}}|$(OPEN_API_SPEC_URL)|g' \
	     $(SB_COMMON_PATH)/scripts/sdk_cli.py > $(PYTHON_SDK_DIR)/$(SERVICE_NAME_CN)_sdk/sdk_cli.py
	@echo "==> Backing up setup.py and pyproject.toml"; \
		cp $(PYTHON_SDK_DIR)/setup.py $(PYTHON_SDK_DIR)/setup.py.bak; \
		cp $(PYTHON_SDK_DIR)/pyproject.toml $(PYTHON_SDK_DIR)/pyproject.toml.bak;
	@echo "==> Updating setup.py to add CLI entry point..."
	@sed -i '/package_data=/i\    entry_points={\n        "console_scripts": [\n            "$(ACRONYM_LC)=$(SERVICE_NAME_CN)_sdk.sdk_cli:cli",\n        ],\n    },' $(PYTHON_SDK_DIR)/setup.py
	@echo "==> Fixing pyproject.toml build backend to use Poetry..."
	@toml set --to-array --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "build-system.requires" "[\"poetry-core>=1.0.0\"]"
	@toml set --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "build-system.build-backend" "poetry.core.masonry.api"
	@echo "==> Adding CLI entry point to [tool.poetry.scripts]..."
	@toml add_section --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "tool.poetry.scripts"
	@toml set --toml-path $(PYTHON_SDK_DIR)/pyproject.toml "tool.poetry.scripts.$(ACRONYM_LC)" "$(SERVICE_NAME_CN)_sdk.sdk_cli:cli"
	@echo "==> Removing [project.scripts] section if it exists..."
	@sed -i '/^\[project\.scripts\]/,/^$$/d' $(PYTHON_SDK_DIR)/pyproject.toml
	@echo "==> SDK generation complete with CLI support"

