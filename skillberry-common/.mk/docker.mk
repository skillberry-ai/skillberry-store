##@ Docker container management

# Docker registry host
REGISTRY_HOST ?= skillberry-1.vpc.cloud9.ibm.com:8800
# change DOCKER_PROJECT to "skillberry" for public images
DOCKER_PROJECT ?= skillberry-dev
# Docker repo name
REPOSITORY_NAME = $(REGISTRY_HOST)/$(DOCKER_PROJECT)
# Docker command
DOCKER := docker


# Base image for skillberry services

# Root image - from which the skillberry base image is built
ROOT_IMAGE := public.ecr.aws/docker/library/python:3.11

# Base image name and tag
BASE_IMAGE_NAME := skillberry-base
BASE_IMAGE_FULL_NAME = $(REPOSITORY_NAME)/$(BASE_IMAGE_NAME)
BASE_IMAGE_TAG := latest

# Base image dockerfile
BASE_DOCKER_FILE := $(SB_COMMON_PATH)/Dockerfile.base


# Image for the current service 

IMAGE_NAME = $(SERVICE_NAME)
CNTR_NAME = $(SERVICE_NAME)

IMAGE_TAG = $(BUILD_VERSION)
FULL_IMAGE_NAME = $(REPOSITORY_NAME)/$(IMAGE_NAME)

DOCKER_FILE ?= Dockerfile


# Search the shell configuration file to check for aliases
# This assumes you are using zsh or bash
# If you are using a different shell, you may need to adjust this accordingly

# Check for Docker alias in shell configuration files
ifneq (,$(wildcard "~/.zshrc"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.zshrc && echo found),found)
DOCKER := podman
endif
endif

ifneq (,$(wildcard "~/.bashrc"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.bashrc && echo found),found)
DOCKER := podman
endif
endif

ifneq (,$(wildcard "~/.bash_profile"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.bash_profile && echo found),found)
DOCKER := podman
endif
endif

ifneq (,$(wildcard "~/.profile"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.profile && echo found),found)
DOCKER := podman
endif
endif

# Print the value of DOCKER
@echo "Using Docker: $(DOCKER)"

# Check whether docker is aliased to podman
# It is assumed that the user is using zsh or bash and alias is defined in ~/.zshrc or ~/.bashrc
# Check that either Docker or Podman is installed
# Check if the user has aliased Docker to Podman in their shell configuration file
# If the user has aliased Docker to Podman, set the DOCKER variable to podman 
# If the user has not aliased Docker to Podman, set the DOCKER variable to docker
docker-check:
	@echo "Checking whether Docker or Podman is installed..."
	@if ! command -v docker > /dev/null && ! command -v podman > /dev/null; then \
        echo "Neither Docker nor Podman is installed. Please install Docker or Podman (or both)."; \
        exit 1; \
    fi

.PHONY: base-image-build 
base-image-build: docker-check .stamps/base-image-build	## Build skillberry base image

# Build base image if it does not exist
.stamps/base-image-build: 
	@echo "Building BASE IMAGE for $(ARCH) using $(DOCKER) version: $(shell $(DOCKER) --version)"
	@echo "Building BASE IMAGE: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
	@echo "Using ROOT IMAGE: $(ROOT_IMAGE)"
	@if [ "$(DOCKER)" = "docker" ]; then \
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build \
		--file $(BASE_DOCKER_FILE) \
		--load \
		--build-arg ROOT_IMAGE=$(ROOT_IMAGE) \
		-t $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) \
		.; \
		touch .stamps/base-image-build; \
	elif [ "$(DOCKER)" = "podman" ]; then \
		$(DOCKER) build --no-cache=true \
		--file $(BASE_DOCKER_FILE) \
		--load \
		--build-arg ROOT_IMAGE=$(ROOT_IMAGE) \
		-t $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) \
		.; \
		touch .stamps/base-image-build; \
    else \
		echo "Unsupported Docker version: $(DOCKER)"; \
		echo "Please use Docker or Podman"; \
		exit 1; \
	fi

# make sure that you are login into the appropriate Docker registry with required credentials
# before running this command
.PHONY: base-image-push
base-image-push: docker-check base-image-build ## Push base image into the registry
	@echo "Pushing BASE image: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
	$(DOCKER) push $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)

.PHONY: base-image-rm
base-image-rm: docker-check ## Remove the local base image
	@echo "Removing BASE image: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
	$(DOCKER) rmi -f $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) > /dev/null 2>&1 || true
	rm -f .stamps/base-image-build

.PHONY: docker-build 
docker-build: docker-check update-git-version .stamps/docker-build	## Build service in docker image

# We actually build a new image only if the code changed by checking code-scan stamp
.stamps/docker-build: .stamps/ssh-agent.env .stamps/code-scan
	@echo "Building for $(ARCH) using $(DOCKER) version: $(shell $(DOCKER) --version)"
	@echo "Building Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Build version: $(BUILD_VERSION)"
	@echo "Build date: $(BUILD_DATE)"
	@echo "Building for $(ARCH) using the Docker file $(DOCKER_FILE): $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	@. .stamps/ssh-agent.env; \
	if [ "$(DOCKER)" = "docker" ]; then \
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build \
		--file $(DOCKER_FILE) \
		--load \
		--build-arg BASE_IMAGE_FULL_NAME=$(BASE_IMAGE_FULL_NAME) \
		--build-arg BASE_IMAGE_TAG=$(BASE_IMAGE_TAG) \
		--build-arg BUILD_VERSION=$(BUILD_VERSION) \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg SERVICE_NAME="$(SERVICE_NAME)" \
		--build-arg SERVICE_PORTS="$(SERVICE_PORTS)" \
		--build-arg SERVICE_ENTRY_MODULE="$(SERVICE_ENTRY_MODULE)" \
		--ssh default=$$SSH_AUTH_SOCK \
		-t $(FULL_IMAGE_NAME):$(IMAGE_TAG) \
		-t $(FULL_IMAGE_NAME):latest \
		. || exit 1; \
		touch .stamps/docker-build; \
	elif [ "$(DOCKER)" = "podman" ]; then \
		$(DOCKER) build --no-cache=true \
		--file $(DOCKER_FILE) \
		--build-arg BASE_IMAGE_FULL_NAME=$(BASE_IMAGE_FULL_NAME) \
		--build-arg BASE_IMAGE_TAG=$(BASE_IMAGE_TAG) \
		--build-arg BUILD_VERSION=$(BUILD_VERSION) \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg SERVICE_NAME="$(SERVICE_NAME)" \
		--build-arg SERVICE_PORTS="$(SERVICE_PORTS)" \
		--build-arg SERVICE_ENTRY_MODULE="$(SERVICE_ENTRY_MODULE)" \
		--ssh default=$$SSH_AUTH_SOCK \
		-t $(FULL_IMAGE_NAME):$(IMAGE_TAG) \
		-t $(FULL_IMAGE_NAME):latest \
		. || exit 1; \
		touch .stamps/docker-build; \
    else \
		echo "Unsupported Docker version: $(DOCKER)"; \
		echo "Please use Docker or Podman"; \
		exit 1; \
	fi

# make sure that you are login into the appropriate Docker registry with required credentials
# before running this command
.PHONY: docker-push
docker-push: docker-check docker-build ## Push docker image into the registry
	@echo "Pushing Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	$(DOCKER) push $(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Pushing Docker image: $(FULL_IMAGE_NAME):latest"
	$(DOCKER) push $(FULL_IMAGE_NAME):latest


.PHONY: docker-run
ifeq ($(USE_LLM_SVCS),1)
docker-run: docker-check docker-build docker-clean check-rits-watsonx-envs
	@$(SB_COMMON_PATH)/scripts/update_env_vars.sh -r .env $(LLM_SVCS_ENV_VARS)
	$(DOCKER) run --name $(CNTR_NAME) --env-file .env \
		-d \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Docker container started: $(CNTR_NAME)"
else
docker-run: docker-check docker-build docker-clean
	$(DOCKER) run --name $(CNTR_NAME) --env-file .env \
		-d \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Docker container started: $(CNTR_NAME)"
endif


.PHONY: docker-rm
docker-rm: docker-check docker-clean ## Remove the docker container, image, and temporary files
	@echo "Removing Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	$(DOCKER) rmi -f $(FULL_IMAGE_NAME):$(IMAGE_TAG) > /dev/null 2>&1 || true
	$(DOCKER) rmi -f $(FULL_IMAGE_NAME):latest > /dev/null 2>&1 || true
	rm -f .stamps/docker-build

.PHONY: docker-clean
docker-clean: docker-check docker-stop ## Remove the docker container and temporary files, but keeping the image
	@echo "Removing Docker container: $(CNTR_NAME)"
	$(DOCKER) rm -f $(CNTR_NAME) > /dev/null 2>&1 || true

.PHONY: docker-stop
docker-stop: docker-check ## Stop the docker container
	@echo "Stopping Docker container: $(CNTR_NAME)"
	$(DOCKER) stop $(CNTR_NAME) > /dev/null 2>&1 || true
	
