
.DEFAULT_GOAL := help

ARCH := $(shell uname -m)

BUILD_VERSION ?= $(ARCH)-$(shell git describe --always --dirty 2>/dev/null || echo "unknown")
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

DOCKER_REPOSITORY_NAME ?= artifactory.haifa.ibm.com:5130
IMAGE_NAME = blueberry-tools-service

DOCKER_NAME = $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME)
DOCKER_VERSION = $(BUILD_VERSION)

DOCKER := docker

TOOLS_SERVICE_SENTINEL=/tmp/tools-service.pid

DOCKER_FILE := Dockerfile

BTS_PORT := $(or $(shell echo $$BTS_PORT), 8000) 
BTS_HOST := $(or $(shell echo $$BTS_HOST), 0.0.0.0)

AWK := awk
OS := $(shell uname -s)

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

ifeq ($(ARCH), arm64)
	DOCKER_FILE := Dockerfile-$(ARCH)
endif


.PHONY: help
help: ## Display this help.
	@$(AWK) 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: git_hooks_setup
git_hooks_setup:
	@git config core.hooksPath .githooks
	@chmod +x .githooks/*

.PHONY: update_git_version
update_git_version:
	@echo "Writing git version to blueberry_tools_service/fast_api/git_version.py"
	@echo "__git_version__ = \"$(BUILD_VERSION)\"" > blueberry_tools_service/fast_api/git_version.py


.PHONY: install_requirements
install_requirements: update_git_version git_hooks_setup # Install requirements
	@PIP_CONFIG_FILE=./pip.conf pip install -e .

install_dev_requirements: # Install dev requirements
	@pip install -e ".[dev]"

##@ Setup & teardown as a process

.PHONY: run install_requirements
run: install_requirements ## Run the tools service
	@if [ -f $(TOOLS_SERVICE_SENTINEL) ]; then \
		echo "Blueberry Tools Service is already running"; \
	else \
		echo "Starting Blueberry Tools Service"; \
		blueberry_tools_service/contrib/scripts/start-service.sh /tmp/tools-service.log $(TOOLS_SERVICE_SENTINEL) python -m blueberry_tools_service.main; \
	fi

stop: $(TOOLS_SERVICE_SENTINEL) ## Stop the tools service
	@echo "Stopping Blueberry Tools Service"
	@blueberry_tools_service/contrib/scripts/stop-service.sh $(TOOLS_SERVICE_SENTINEL)

clean:  ## Clean temporary files
	@rm -f $(TOOLS_SERVICE_SENTINEL)
	-rm -rf __pycache__ .pytest_cache
	@echo "Clean blueberry-tools-service /tmp directory"
	+rm -rf /tmp/manifest
	+rm -rf /tmp/descriptions
	+rm -rf /tmp/files

	rm -rf build dist *.egg-info	

##@ Docker

# Check whether docker is aliased to podman
# I is assumed that the user is using zsh or bash and alias is defined in ~/.zshrc or ~/.bashrc
# Check that either Docker or Podman is installed
# Check if the user has aliased Docker to Podman in their shell configuration file
# If the user has aliased Docker to Podman, set the DOCKER variable to podman 
# If the user has not aliased Docker to Podman, set the DOCKER variable to docker
docker_check:
	@echo "Checking whether Docker or Podman is installed..."
	@if ! command -v docker > /dev/null && ! command -v podman > /dev/null; then \
        echo "Neither Docker nor Podman is installed. Please install Docker or Podman (or both)."; \
        exit 1; \
    fi

	@echo "Checking for Docker or Podman aliases..."
# Search the shell configuration file to check for aliases
# This assumes you are using zsh or bash
# If you are using a different shell, you may need to adjust this accordingly

# Check for Docker alias in shell configuration files
ifeq ($(shell grep -q "alias docker='podman'" ~/.zshrc && echo found),found)
DOCKER := podman
endif

ifeq ($(shell grep -q "alias docker='podman'" ~/.bashrc && echo found),found)
DOCKER := podman
endif

ifeq ($(shell grep -q "alias docker='podman'" ~/.bash_profile && echo found),found)
DOCKER := podman
endif

ifeq ($(shell grep -q "alias docker='podman'" ~/.profile && echo found),found)
DOCKER := podman
endif

# Print the value of DOCKER
@echo "Using Docker: $(DOCKER)"

.PHONY: docker_build 
docker_build: docker_check update_git_version ## Build docker image for arm64 and amd64
	@echo "Building for $(ARCH) using $(DOCKER) version: $(shell $(DOCKER) --version)"
	@echo "Building Docker image: $(DOCKER_NAME):$(DOCKER_VERSION)"
	@echo "Build version: $(BUILD_VERSION)"
	@echo "Build date: $(BUILD_DATE)"
	@echo "Building for $(ARCH) using the Docker file $(DOCKER_FILE): $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"
	@if [ "$(DOCKER)" = "docker" ]; then \
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build --file $(DOCKER_FILE) --load --build-arg BUILD_VERSION=$(BUILD_VERSION) --build-arg BUILD_DATE="$(BUILD_DATE)" -t $(DOCKER_NAME):$(DOCKER_VERSION) .; \
	elif [ "$(DOCKER)" = "podman" ]; then \
		$(DOCKER) build --no-cache=true --file $(DOCKER_FILE) --build-arg BUILD_VERSION=$(BUILD_VERSION) --build-arg BUILD_DATE="$(BUILD_DATE)" -t $(DOCKER_NAME):$(DOCKER_VERSION) .; \
    else \
		echo "Unsupported Docker version: $(DOCKER)"; \
		echo "Please use Docker or Podman"; \
		exit 1; \
	fi

.PHONY: docker_run
docker_run: docker_check docker_stop ## Run the docker image
	$(DOCKER) run --privileged --name $(IMAGE_NAME) --env-file .env -e BTS_HOST=$(strip $(BTS_HOST)) -e BTS_PORT=$(strip $(BTS_PORT)) -d -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp -p $(strip $(BTS_PORT)):$(strip $(BTS_PORT)) $(DOCKER_NAME):$(DOCKER_VERSION)
	@echo "Docker container started: $(IMAGE_NAME)"
	

.PHONY: docker_rm
docker_rm: docker_stop clean ## Remove the docker container, image, and temporary files
	@echo "Removing Docker container: $(IMAGE_NAME)"
	$(DOCKER) rm -f $(IMAGE_NAME) > /dev/null 2>&1 || true
	@echo "Removing Docker image: $(DOCKER_NAME):$(DOCKER_VERSION)"
	$(DOCKER) rmi -f $(DOCKER_NAME):$(DOCKER_VERSION) > /dev/null 2>&1 || true
	@echo "Removing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"


.PHONY: docker_clean
docker_clean: docker_stop clean ## Remove the docker container and temporary files, but keeping the image
	@echo "Removing Docker container: $(IMAGE_NAME)"
	$(DOCKER) rm -f $(IMAGE_NAME) > /dev/null 2>&1 || true

.PHONY: docker_stop
docker_stop: docker_check ## Stop the docker image
	@echo "Stopping Docker container: $(IMAGE_NAME)"
	$(DOCKER) stop $(IMAGE_NAME) > /dev/null 2>&1 || true
	$(DOCKER) rm $(IMAGE_NAME) > /dev/null 2>&1 || true
	
# make sure that you are login into the appropriate Docker registry with required credentials
# before running this command
# set up the credentials in ~/.docker/config.json according to the instructions in artifactory.haifa.ibm.com
.PHONY: docker_push
docker_push: docker_check docker_build ## Push docker image into the registry
	@echo "Pushing Docker image: $(DOCKER_NAME):$(DOCKER_VERSION)"
	@echo "Pushing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"
	$(DOCKER) push $(DOCKER_NAME):$(DOCKER_VERSION)

include .mk/development.mk
include .mk/ci.mk
