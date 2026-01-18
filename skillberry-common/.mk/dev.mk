##@ Development

# List here all supported Python version specs (one or more separated by space). 
# Spec options: v1 v1.v2 v1.v2.v3
# Can add "+" to specify minimal version
# Example: 3.13+ 3.12.9 3.11.5+
SUPPORTED_PYTHON_VERSIONS := 3.11

# List your subtree roots
CODE_SUBTREES := src .mk $(SB_COMMON_PATH)/.mk $(SB_COMMON_PATH)/scripts

# One common filter for all
CODE_FILTER := \( -name '*.py' -o -name 'Makefile' -o -name '*.mk' -o -name '*.sh' \)

# Expand to the union of files across all subtrees
CODE_FILES := $(foreach T,$(CODE_SUBTREES), \
  $(shell find $(T) -type f $(CODE_FILTER) -print))

CODE_FILES := $(CODE_FILES) pyproject.toml Makefile

# This stamp file checks for code changes
.stamps/code_scan: $(CODE_FILES) 
	@echo "Detected code changed in: $(CODE_SUBTREES)"
	@touch .stamps/code_scan

git_hooks_setup:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    echo "Setting up Git hooks..."; \
	    git config core.hooksPath .githooks; \
	    chmod +x .githooks/*; \
	else \
	    echo "Skipping git_hooks_setup: not inside a Git repository."; \
	fi

test: install_requirements ## Test the tools-service
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

.PHONY: install_requirements verify_venv
install_requirements: update_git_version git_hooks_setup verify_venv .stamps/install_requirements-$(ODEPS) ## Install dependencies. For opt. deps: make install_requirements ODEPS=dev,vllm
	@true

verify_venv:
	@$(SB_COMMON_PATH)/scripts/check_venv.sh $(SUPPORTED_PYTHON_VERSIONS)
	@pip install uv

# Need to actually install only when pyproject.toml changes
.stamps/install_requirements-$(ODEPS): pyproject.toml
	@ODEPS="$(ODEPS)"; \
	if [ -z "$$ODEPS" ]; then \
		uv pip install -e .; \
	else \
		uv pip install -e .[$(ODEPS)]; \
	fi
	@touch .stamps/install_requirements-$(ODEPS)



.PHONY: update_git_version
update_git_version:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    echo "Writing git version to $(VERSION_LOCATION)"; \
	    echo "__git_version__ = \"$(BUILD_VERSION)\"" > $(VERSION_LOCATION); \
	else \
	    echo "Skipping update_git_version: not inside a Git repository."; \
	fi

