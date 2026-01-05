##@ Development

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

.PHONY: install_requirements
install_requirements: update_git_version git_hooks_setup # Install requirements
	@PIP_CONFIG_FILE=./pip.conf pip install -e .

.PHONY: install_dev_requirements
install_dev_requirements: # Install dev requirements
	@pip install -e ".[dev]"

.PHONY: update_git_version
update_git_version:
	@if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then \
	    echo "Writing git version to $(VERSION_LOCATION)"; \
	    echo "__git_version__ = \"$(BUILD_VERSION)\"" > $(VERSION_LOCATION); \
	else \
	    echo "Skipping update_git_version: not inside a Git repository."; \
	fi


