##@ Docker container management

# Supported container architectures
SUPPORTED_ARCHS := linux/amd64 linux/arm64

# Docker registry host
REGISTRY_HOST ?= ghcr.io
# change DOCKER_PROJECT to "skillberry" for public images
DOCKER_PROJECT ?= skillberry-ai
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

# Container volume mounts as docker run args
VOLUME_FLAGS = $(foreach vol,$(CNTR_MOUNTS),-v $(vol))


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

# Compute DOCKER_ARCH based on the container runtime. Value is docker-specific, e.g., linux/amd64, linux/arm64, etc.
# If the container runtime is not recognized, the value is set to "unknown"
ifeq ($(DOCKER),docker)
DOCKER_ARCH := $(shell docker version --format '{{.Server.Os}}/{{.Server.Arch}}' 2>/dev/null || echo "unknown")
else ifeq ($(DOCKER),podman)
DOCKER_ARCH := $(shell podman info --format '{{.Host.OS}}/{{.Host.Arch}}' 2>/dev/null || echo "unknown")
else
DOCKER_ARCH := unknown
endif

# Print the value of DOCKER
@echo "Using Docker: $(DOCKER)"

# Check whether docker is aliased to podman
# It is assumed that the user is using zsh or bash and alias is defined in ~/.zshrc or ~/.bashrc
# Check that either Docker or Podman is installed
# Check if the user has aliased Docker to Podman in their shell configuration file
# If the user has aliased Docker to Podman, set the DOCKER variable to podman 
# If the user has not aliased Docker to Podman, set the DOCKER variable to docker
.PHONY: docker-check 
docker-check:
	@echo "Checking whether Docker or Podman is installed..."
	@if ! command -v docker > /dev/null && ! command -v podman > /dev/null; then \
        echo "Neither Docker nor Podman is installed. Please install Docker or Podman (or both)."; \
        exit 1; \
    fi

.PHONY: multiarch-check
multiarch-check:
	@echo "Verifying multi-arch container build is enabled and supports: $(SUPPORTED_ARCHS)"
	@$(SB_COMMON_PATH)/scripts/check-multiarch.sh $(DOCKER) $(SUPPORTED_ARCHS) || exit 1

# DBT - Docker Build Target: "local" for local build and "registry" for pushing the built image to registry. Default - local
DBT ?= local

ifeq ($(DBT),local)
	DB_ARCH := $(DOCKER_ARCH)
	DB_ACTION := load
else ifeq ($(DBT),registry)
	DB_ARCH := $(SUPPORTED_ARCHS)
	DB_ACTION := push
else
	@echo "Invalid DBT value: $(DBT). Supported values: local, registry"
	@exit 1
endif

.PHONY: base-image-build 
base-image-build: multiarch-check .stamps/base-image-build-$(DBT)	## Build skillberry base image (DBT=registry to build & push multi-arch)

# Build base multi-arch image if it does not exist
.stamps/base-image-build-$(DBT): 
	@echo "Building Base Image using $(DOCKER) version: $(shell $(DOCKER) --version)"
	@echo "Supported Architectures: $(DB_ARCH)"
	@echo "Base Image Name: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
	@echo "Using ROOT IMAGE: $(ROOT_IMAGE)"
	@if [ "$(DOCKER)" = "docker" ]; then \
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build \
		--file $(BASE_DOCKER_FILE) \
		--platform $(call to_csv,$(DB_ARCH)) \
		--build-arg ROOT_IMAGE=$(ROOT_IMAGE) \
		-t $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) \
		--$(DB_ACTION) \
		. \
		|| exit 1; \
		touch .stamps/base-image-build-$(DBT); \
	elif [ "$(DOCKER)" = "podman" ]; then \
		if [ "$(DBT)" = "registry" ]; then \
			$(DOCKER) build --no-cache=true \
			--file $(BASE_DOCKER_FILE) \
			--platform $(call to_csv,$(DB_ARCH)) \
			--build-arg ROOT_IMAGE=$(ROOT_IMAGE) \
			--manifest $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) \
			. && \
			$(DOCKER) manifest push $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) \
			|| exit 1; \
		else \
			$(DOCKER) build --no-cache=true \
			--file $(BASE_DOCKER_FILE) \
			--platform $(DB_ARCH) \
			--build-arg ROOT_IMAGE=$(ROOT_IMAGE) \
			-t $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) \
			. || exit 1; \
		fi; \
		touch .stamps/base-image-build-$(DBT); \
    else \
		echo "Unsupported Docker version: $(DOCKER)"; \
		echo "Please use Docker or Podman"; \
		exit 1; \
	fi

# make sure that you are login into the appropriate Docker registry with required credentials
# before running this command
# .PHONY: base-image-push
# base-image-push: docker-check base-image-build ## Push base image into the registry
# 	@echo "Pushing BASE image: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
# 	$(DOCKER) push $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)

.PHONY: base-image-rm
base-image-rm: docker-check ## Remove the local base image
	@echo "Removing BASE image: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
	$(DOCKER) rmi -f $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) > /dev/null 2>&1 || true
	rm -f .stamps/base-image-build*

.PHONY: docker-build 
docker-build: docker-check update-git-version .stamps/docker-build-$(DBT)	## Build docker image (DBT=registry to build & push multi-arch)

# We actually build a new image only if the code changed by checking code-scan stamp
.stamps/docker-build-$(DBT): .stamps/ssh-agent.env .stamps/code-scan
	@echo "Building for $(DB_ARCH) using $(DOCKER) version: $(shell $(DOCKER) --version)"
	@echo "Building Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Build version: $(BUILD_VERSION)"
	@echo "Build date: $(BUILD_DATE)"
	@echo "Building using the Docker file: $(DOCKER_FILE)"
	@. .stamps/ssh-agent.env; \
	if [ "$(DOCKER)" = "docker" ]; then \
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build \
		--file $(DOCKER_FILE) \
		--platform $(call to_csv,$(DB_ARCH)) \
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
		--$(DB_ACTION) \
		. || exit 1; \
		touch .stamps/docker-build-$(DBT); \
		touch .stamps/docker-get; \
	elif [ "$(DOCKER)" = "podman" ]; then \
		if [ "$(DBT)" = "registry" ]; then \
			$(DOCKER) build --no-cache=true \
			--file $(DOCKER_FILE) \
			--platform $(call to_csv,$(DB_ARCH)) \
			--build-arg BASE_IMAGE_FULL_NAME=$(BASE_IMAGE_FULL_NAME) \
			--build-arg BASE_IMAGE_TAG=$(BASE_IMAGE_TAG) \
			--build-arg BUILD_VERSION=$(BUILD_VERSION) \
			--build-arg BUILD_DATE="$(BUILD_DATE)" \
			--build-arg SERVICE_NAME="$(SERVICE_NAME)" \
			--build-arg SERVICE_PORTS="$(SERVICE_PORTS)" \
			--build-arg SERVICE_ENTRY_MODULE="$(SERVICE_ENTRY_MODULE)" \
			--ssh default=$$SSH_AUTH_SOCK \
			--manifest $(FULL_IMAGE_NAME):$(IMAGE_TAG) \
			. && \
			$(DOCKER) manifest push $(FULL_IMAGE_NAME):$(IMAGE_TAG) && \
			$(DOCKER) tag $(FULL_IMAGE_NAME):$(IMAGE_TAG) $(FULL_IMAGE_NAME):latest && \
			$(DOCKER) manifest push $(FULL_IMAGE_NAME):latest \
			|| exit 1; \
		else \
			$(DOCKER) build --no-cache=true \
			--file $(DOCKER_FILE) \
			--platform $(DB_ARCH) \
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
		fi; \
		touch .stamps/docker-build-$(DBT); \
		touch .stamps/docker-get; \
    else \
		echo "Unsupported Docker version: $(DOCKER)"; \
		echo "Please use Docker or Podman"; \
		exit 1; \
	fi

# make sure that you are logged into the appropriate Docker registry with required credentials
# before running this command
# .PHONY: docker-push
# docker-push: docker-check docker-build ## Push docker image into the registry
# 	@echo "Pushing Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
# 	$(DOCKER) push $(FULL_IMAGE_NAME):$(IMAGE_TAG)
# 	@echo "Pushing Docker image: $(FULL_IMAGE_NAME):latest"
# 	$(DOCKER) push $(FULL_IMAGE_NAME):latest


.PHONY: docker-pull
docker-pull: docker-check ## Pull the latest docker image from registry
	@echo "Attempting to pull Docker image: $(FULL_IMAGE_NAME):latest"
	@if $(DOCKER) pull $(FULL_IMAGE_NAME):latest; then \
		echo "✓ Successfully pulled image: $(FULL_IMAGE_NAME):latest"; \
		$(DOCKER) tag $(FULL_IMAGE_NAME):latest $(FULL_IMAGE_NAME):$(IMAGE_TAG); \
		echo "✓ Tagged as: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"; \
		touch .stamps/docker-get; \
	else \
		echo "✗ Failed to pull image: $(FULL_IMAGE_NAME):latest"; \
		exit 1; \
	fi

.PHONY: docker-get
docker-get: .stamps/docker-get
	@true

ifdef SBD_DEV
.stamps/docker-get: docker-build ## Get docker image (SBD_DEV set: build only)
	@echo "SBD_DEV is set - using locally built image"
else
.stamps/docker-get: ## Get docker image (pull latest or build if pull fails)
	@echo "Attempting to get Docker image: $(FULL_IMAGE_NAME):latest"
	@if $(MAKE) docker-pull; then \
		echo "✓ Using pulled image"; \
	else \
		echo "⚠ Pull failed - falling back to building image locally"; \
		$(MAKE) docker-build; \
	fi
endif

.PHONY: docker-run
ifeq ($(USE_LLM_SVCS),1)
docker-run: docker-check docker-get docker-clean check-rits-watsonx-envs ## Run the docker container (pull or build first if needed)
	@$(SB_COMMON_PATH)/scripts/update_env_vars.sh -r .env $(LLM_SVCS_ENV_VARS)
	$(DOCKER) run --name $(CNTR_NAME) --env-file .env \
		-d \
		$(VOLUME_FLAGS) \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Docker container started: $(CNTR_NAME)"
else
docker-run: docker-check docker-get docker-clean
	$(DOCKER) run --name $(CNTR_NAME) --env-file .env \
		-d \
		$(VOLUME_FLAGS) \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Docker container started: $(CNTR_NAME)"
endif

.PHONY: docker-rmi
docker-rmi: docker-check docker-clean ## Remove the docker container, image, and temporary files
	@echo "Removing Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	@$(DOCKER) rmi -f $(FULL_IMAGE_NAME):$(IMAGE_TAG) > /dev/null 2>&1 || true
	@$(DOCKER) rmi -f $(FULL_IMAGE_NAME):latest > /dev/null 2>&1 || true
	@rm -f .stamps/docker-build*
	@rm -f .stamps/docker-get 

.PHONY: docker-clean
docker-clean: docker-check docker-stop ## Remove the docker container and temporary files, but keeping the image
	@echo "Removing Docker container: $(CNTR_NAME)"
	$(DOCKER) rm -f $(CNTR_NAME) > /dev/null 2>&1 || true

.PHONY: docker-stop
docker-stop: docker-check ## Stop the docker container
	@echo "Stopping Docker container: $(CNTR_NAME)"
	$(DOCKER) stop $(CNTR_NAME) > /dev/null 2>&1 || true
	
