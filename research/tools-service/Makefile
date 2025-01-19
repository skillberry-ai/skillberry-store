
.DEFAULT_GOAL := help

VERSION ?= latest
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

install_requirements: # Install dependencies
	@pip install -q -r requirements.txt

##@ Execute

run: install_requirements ## Run the application
	python main.py


clean: install_requirements ## Clean temporary files
	rm -rf __pycache__ .pytest_cache
