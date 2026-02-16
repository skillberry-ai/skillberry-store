##@ Docker container management

DOCKER_HOST ?= skillberry-1.vpc.cloud9.ibm.com:8800
# change DOCKER_PROJECT to "skillberry" for public images
DOCKER_PROJECT ?= skillberry-dev

DOCKER_REPOSITORY_NAME = $(DOCKER_HOST)/$(DOCKER_PROJECT)
IMAGE_NAME = $(SERVICE_NAME)

DOCKER_NAME = $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME)
DOCKER_VERSION = $(BUILD_VERSION)

DOCKER := docker

DOCKER_FILE ?= Dockerfile

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

	@echo "Checking for Docker or Podman aliases..."
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

.PHONY: docker-build 
docker-build: docker-check update-git-version .stamps/docker-build

# We actually build a new image only if the code changed
.stamps/docker-build: .stamps/code-scan
	@echo "Building for $(ARCH) using $(DOCKER) version: $(shell $(DOCKER) --version)"
	@echo "Building Docker image: $(DOCKER_NAME):$(DOCKER_VERSION)"
	@echo "Build version: $(BUILD_VERSION)"
	@echo "Build date: $(BUILD_DATE)"
	@echo "Building for $(ARCH) using the Docker file $(DOCKER_FILE): $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"
	@if [ "$(DOCKER)" = "docker" ]; then \
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build \
		--file $(DOCKER_FILE) \
		--load \
		--build-arg BUILD_VERSION=$(BUILD_VERSION) \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg SERVICE_NAME="$(SERVICE_NAME)" \
		--build-arg SERVICE_PORTS="$(SERVICE_PORTS)" \
		--build-arg SERVICE_ENTRY_MODULE="$(SERVICE_ENTRY_MODULE)" \
		-t $(DOCKER_NAME):$(DOCKER_VERSION) \
		-t $(DOCKER_NAME):latest \
		.; \
		touch .stamps/docker-build; \
	elif [ "$(DOCKER)" = "podman" ]; then \
		$(DOCKER) build --no-cache=true \
		--file $(DOCKER_FILE) \
		--build-arg BUILD_VERSION=$(BUILD_VERSION) \
		--build-arg BUILD_DATE="$(BUILD_DATE)" \
		--build-arg SERVICE_NAME="$(SERVICE_NAME)" \
		--build-arg SERVICE_PORTS="$(SERVICE_PORTS)" \
		--build-arg SERVICE_ENTRY_MODULE="$(SERVICE_ENTRY_MODULE)" \
		-t $(DOCKER_NAME):$(DOCKER_VERSION) \
		-t $(DOCKER_NAME):latest \
		.; \
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
	@echo "Pushing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"
	$(DOCKER) push $(DOCKER_NAME):$(DOCKER_VERSION)
	@echo "Pushing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):latest"
	$(DOCKER) push $(DOCKER_NAME):latest

.PHONY: docker-run
docker-run:  docker-check docker-build docker-stop ## Run the docker image
	$(DOCKER) run --name $(IMAGE_NAME) --env-file .env \
		-d \
		--network=host \
		$(DOCKER_NAME):$(DOCKER_VERSION)
	@echo "Docker container started: $(IMAGE_NAME)"
	

.PHONY: docker-rm
docker-rm: docker-check docker-stop clean ## Remove the docker container, image, and temporary files
	@echo "Removing Docker container: $(IMAGE_NAME)"
	$(DOCKER) rm -f $(IMAGE_NAME) > /dev/null 2>&1 || true
	@echo "Removing Docker image: $(DOCKER_NAME):$(DOCKER_VERSION)"
	$(DOCKER) rmi -f $(DOCKER_NAME):$(DOCKER_VERSION) > /dev/null 2>&1 || true
	@echo "Removing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"


.PHONY: docker-clean
docker-clean: docker-check docker-stop ## Remove the docker container and temporary files, but keeping the image
	@echo "Removing Docker container: $(IMAGE_NAME)"
	$(DOCKER) rm -f $(IMAGE_NAME) > /dev/null 2>&1 || true

.PHONY: docker-stop
docker-stop: docker-check ## Stop the docker container
	@echo "Stopping Docker container: $(IMAGE_NAME)"
	$(DOCKER) stop $(IMAGE_NAME) > /dev/null 2>&1 || true
	$(DOCKER) rm $(IMAGE_NAME) > /dev/null 2>&1 || true
	
