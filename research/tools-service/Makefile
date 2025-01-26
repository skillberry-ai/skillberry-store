
.DEFAULT_GOAL := help

VERSION ?= latest
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

AWK := awk
ifeq ($(OS),Windows_NT)
		AWK = gawk
		ifeq (, $(shell where gawk 2> NUL))
			$(error "gawk not found. Please install it and ensure it's in your PATH.")
		endif
else
	ifeq ($(shell uname -s), Darwin)
		AWK = gawk
		ifeq (, $(shell which gawk 2> /dev/null))
			$(error "gawk not found. Please install it and ensure it's in your PATH.")
		endif
	endif
endif

.PHONY: help
help: ## Display this help.
	@$(AWK) 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

install_requirements: # Install dependencies
	@pip install -q -r requirements.txt

##@ Execute

run: install_requirements ## Run the application
	python main.py

test: install_requirements ## Test the application
	pytest

clean:  ## Clean temporary files
	-rm -rf __pycache__ .pytest_cache

##@ Develop
load_tools:  ## Loading tools from the contrib directory to the service
	./contrib/load_tools_into_service.sh

delete_tools:  ## clean tool directories from /tmp
	-rm -rf /tmp/files
	-rm -rf /tmp/descriptions
	-rm -rf /tmp/metadata
