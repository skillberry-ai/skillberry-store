# =============================================================================
# Docker Container Management
# =============================================================================
# This file contains targets for building, running, and managing Docker containers.
# It supports both Docker and Podman, with automatic detection and multi-architecture builds.
#
# Key targets:
#   - docker-run: Run the service in a container (auto-pull or build)
#   - docker-build: Build the Docker image
#   - docker-stop: Stop the running container
#   - docker-clean: Remove the container (keeps image)
#   - docker-rmi: Remove container and image
#
# Build modes (DBT variable):
#   - DBT=local (default): Build for current architecture only
#   - DBT=registry: Build for all architectures and push to registry
#
# Development mode:
#   - SBD_DEV=1: Skip pull, always build locally
# =============================================================================

##@ Docker container management

# -----------------------------------------------------------------------------
# Architecture Support
# -----------------------------------------------------------------------------
# List of architectures to build for when pushing to registry
# Multi-arch builds require Docker buildx or Podman manifest support
SUPPORTED_ARCHS := linux/amd64 linux/arm64

# -----------------------------------------------------------------------------
# Registry Configuration
# -----------------------------------------------------------------------------
# Docker registry host (GitHub Container Registry)
REGISTRY_HOST ?= ghcr.io

# Docker project/organization name
# Use "skillberry" for public images, "skillberry-ai" for private
DOCKER_PROJECT ?= skillberry-ai

# Full repository name (host + project)
REPOSITORY_NAME = $(REGISTRY_HOST)/$(DOCKER_PROJECT)

# Container runtime command (docker or podman)
DOCKER := docker

# -----------------------------------------------------------------------------
# Base Image Configuration
# -----------------------------------------------------------------------------
# The base image contains common dependencies shared across Skillberry services
# This reduces build times and ensures consistency

# Root image that the base image is built from
ROOT_IMAGE := python:3.11-slim

# Base image name and tag
BASE_IMAGE_NAME := skillberry-base
BASE_IMAGE_FULL_NAME = $(REPOSITORY_NAME)/$(BASE_IMAGE_NAME)
BASE_IMAGE_TAG := latest

# Dockerfile for building the base image
BASE_DOCKER_FILE := $(SB_COMMON_PATH)/Dockerfile.base

# -----------------------------------------------------------------------------
# Service Image Configuration
# -----------------------------------------------------------------------------
# Configuration for the current service's Docker image

# Image name (same as service name)
IMAGE_NAME = $(SERVICE_NAME)

# Container name when running
CNTR_NAME = $(SERVICE_NAME)

# Image tag (uses calculated BUILD_VERSION)
IMAGE_TAG = $(BUILD_VERSION)

# Full image name with registry
FULL_IMAGE_NAME = $(REPOSITORY_NAME)/$(IMAGE_NAME)

# Dockerfile for building the service image
DOCKER_FILE ?= Dockerfile

# Volume mounts for the container (defined in project's .mk/local.mk)
# Format: -v /host/path:/container/path
VOLUME_FLAGS = $(foreach vol,$(CNTR_MOUNTS),-v $(vol))

# -----------------------------------------------------------------------------
# Container Runtime Detection
# -----------------------------------------------------------------------------
# Auto-detect if Docker is aliased to Podman in shell configuration files
# This allows seamless switching between Docker and Podman

# Check ~/.zshrc for Docker->Podman alias
ifneq (,$(wildcard "~/.zshrc"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.zshrc && echo found),found)
DOCKER := podman
endif
endif

# Check ~/.bashrc for Docker->Podman alias
ifneq (,$(wildcard "~/.bashrc"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.bashrc && echo found),found)
DOCKER := podman
endif
endif

# Check ~/.bash_profile for Docker->Podman alias
ifneq (,$(wildcard "~/.bash_profile"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.bash_profile && echo found),found)
DOCKER := podman
endif
endif

# Check ~/.profile for Docker->Podman alias
ifneq (,$(wildcard "~/.profile"))
ifeq ($(shell grep -q "alias docker='podman'" ~/.profile && echo found),found)
DOCKER := podman
endif
endif

# -----------------------------------------------------------------------------
# Architecture Detection
# -----------------------------------------------------------------------------
# Detect the current platform's architecture
# Format: linux/amd64, linux/arm64, etc.
ifeq ($(DOCKER),docker)
DOCKER_ARCH := $(shell docker version --format '{{.Server.Os}}/{{.Server.Arch}}' 2>/dev/null || echo "unknown")
else ifeq ($(DOCKER),podman)
DOCKER_ARCH := $(shell podman info --format '{{.Host.OS}}/{{.Host.Arch}}' 2>/dev/null || echo "unknown")
else
DOCKER_ARCH := unknown
endif

# Print detected container runtime
@echo "Using Docker: $(DOCKER)"

# -----------------------------------------------------------------------------
# Runtime Verification
# -----------------------------------------------------------------------------
# Verify that either Docker or Podman is installed
.PHONY: docker-check 
docker-check:
	@echo "Checking whether Docker or Podman is installed..."
	@if ! command -v docker > /dev/null && ! command -v podman > /dev/null; then \
        echo "Neither Docker nor Podman is installed. Please install Docker or Podman (or both)."; \
        exit 1; \
    fi

# Verify multi-architecture build support
# Required for building images that work on both Intel and ARM processors
.PHONY: multiarch-check
multiarch-check:
	@echo "Verifying multi-arch container build is enabled and supports: $(SUPPORTED_ARCHS)"
	@$(SB_COMMON_PATH)/scripts/check-multiarch.sh $(DOCKER) $(SUPPORTED_ARCHS) || exit 1

# -----------------------------------------------------------------------------
# Build Target Configuration
# -----------------------------------------------------------------------------
# DBT (Docker Build Target) controls where images are built and pushed
# - local: Build for current architecture only, load into local Docker
# - registry: Build for all architectures, push to container registry

DBT ?= local

ifeq ($(DBT),local)
	# Local build: single architecture, load into Docker
	DB_ARCH := $(DOCKER_ARCH)
	DB_ACTION := load
else ifeq ($(DBT),registry)
	# Registry build: all architectures, push to registry
	DB_ARCH := $(SUPPORTED_ARCHS)
	DB_ACTION := push
else
	@echo "Invalid DBT value: $(DBT). Supported values: local, registry"
	@exit 1
endif

# -----------------------------------------------------------------------------
# Base Image Management
# -----------------------------------------------------------------------------
# Build the Skillberry base image
# This image contains common dependencies and is used by all services
.PHONY: base-image-build 
base-image-build: multiarch-check .stamps/base-image-build-$(DBT)	## Build skillberry base image (DBT=registry to build & push multi-arch)

# Build base image only if it doesn't exist or code changed
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

# Remove the local base image
.PHONY: base-image-rm
base-image-rm: docker-check ## Remove the local base image
	@echo "Removing BASE image: $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG)"
	$(DOCKER) rmi -f $(BASE_IMAGE_FULL_NAME):$(BASE_IMAGE_TAG) > /dev/null 2>&1 || true
	rm -f .stamps/base-image-build*

# -----------------------------------------------------------------------------
# Service Image Management
# -----------------------------------------------------------------------------
# Build the service's Docker image
# This includes the service code and dependencies
.PHONY: docker-build 
docker-build: docker-check update-git-version .stamps/docker-build-$(DBT)	## Build docker image (DBT=registry to build & push multi-arch)

# Build service image only if code changed (tracked by code-scan stamp)
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

# -----------------------------------------------------------------------------
# Image Distribution
# -----------------------------------------------------------------------------
# Pull the latest image from the container registry
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

# Get the Docker image (pull or build based on SBD_DEV setting)
.PHONY: docker-get
docker-get: .stamps/docker-get
	@true

# If SBD_DEV is set, always build locally (skip pull)
ifdef SBD_DEV
.stamps/docker-get: docker-build ## Get docker image (SBD_DEV set: build only)
	@echo "SBD_DEV is set - using locally built image"
else
# Otherwise, try to pull first, fall back to building if pull fails
.stamps/docker-get: ## Get docker image (pull latest or build if pull fails)
	@echo "Attempting to get Docker image: $(FULL_IMAGE_NAME):latest"
	@if $(MAKE) docker-pull; then \
		echo "✓ Using pulled image"; \
	else \
		echo "⚠ Pull failed - falling back to building image locally"; \
		$(MAKE) docker-build; \
	fi
endif

# -----------------------------------------------------------------------------
# Container Lifecycle
# -----------------------------------------------------------------------------
# Run the service in a Docker container
# Automatically handles environment variables and port mapping
.PHONY: docker-run
ifeq ($(USE_LLM_SVCS),1)
# If using LLM services, check credentials and pass them to container
docker-run: docker-check docker-get docker-clean check-rits-watsonx-envs ## Run the docker container (pull or build first if needed)
	@$(SB_COMMON_PATH)/scripts/update_env_vars.sh -r .env $(LLM_SVCS_ENV_VARS)
	$(DOCKER) run --name $(CNTR_NAME) --env-file .env \
		-d \
		$(VOLUME_FLAGS) \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Docker container started: $(CNTR_NAME)"
else
# Standard run without LLM service credentials
docker-run: docker-check docker-get docker-clean
	@test -f .env || touch .env
	$(DOCKER) run --name $(CNTR_NAME) --env-file .env \
		-d \
		$(VOLUME_FLAGS) \
		--network=host \
		$(FULL_IMAGE_NAME):$(IMAGE_TAG)
	@echo "Docker container started: $(CNTR_NAME)"
endif

# Remove the Docker image and container
.PHONY: docker-rmi
docker-rmi: docker-check docker-clean ## Remove the docker container, image, and temporary files
	@echo "Removing Docker image: $(FULL_IMAGE_NAME):$(IMAGE_TAG)"
	@$(DOCKER) rmi -f $(FULL_IMAGE_NAME):$(IMAGE_TAG) > /dev/null 2>&1 || true
	@$(DOCKER) rmi -f $(FULL_IMAGE_NAME):latest > /dev/null 2>&1 || true
	@rm -f .stamps/docker-build*
	@rm -f .stamps/docker-get 

# Remove the container but keep the image
.PHONY: docker-clean
docker-clean: docker-check docker-stop ## Remove the docker container and temporary files, but keeping the image
	@echo "Removing Docker container: $(CNTR_NAME)"
	$(DOCKER) rm -f $(CNTR_NAME) > /dev/null 2>&1 || true

# Stop the running container
.PHONY: docker-stop
docker-stop: docker-check ## Stop the docker container
	@echo "Stopping Docker container: $(CNTR_NAME)"
	$(DOCKER) stop $(CNTR_NAME) > /dev/null 2>&1 || true