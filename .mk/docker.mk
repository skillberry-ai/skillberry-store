##@ Docker container management

SERVICE_DOCKER_SETUP ?= ""

# Check whether docker is aliased to podman
# It is assumed that the user is using zsh or bash and alias is defined in ~/.zshrc or ~/.bashrc
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
		DOCKER_BUILDKIT=1 $(DOCKER) buildx build --file $(DOCKER_FILE) --load --build-arg BUILD_VERSION=$(BUILD_VERSION) --build-arg BUILD_DATE="$(BUILD_DATE)" -t $(DOCKER_NAME):$(DOCKER_VERSION) -t $(DOCKER_NAME):latest .; \
	elif [ "$(DOCKER)" = "podman" ]; then \
		$(DOCKER) build --no-cache=true --file $(DOCKER_FILE) --build-arg BUILD_VERSION=$(BUILD_VERSION) --build-arg BUILD_DATE="$(BUILD_DATE)" -t $(DOCKER_NAME):$(DOCKER_VERSION) -t $(DOCKER_NAME):latest .; \
    else \
		echo "Unsupported Docker version: $(DOCKER)"; \
		echo "Please use Docker or Podman"; \
		exit 1; \
	fi

.PHONY: docker_run
docker_run: docker_check docker_stop ## Run the docker image
	$(DOCKER) run --privileged --name $(IMAGE_NAME) --env-file .env \
		$(SERVICE_DOCKER_SETUP) \
		-d -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp \
		--network=host \
		$(DOCKER_NAME):$(DOCKER_VERSION)
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
.PHONY: docker_push
docker_push: docker_check docker_build ## Push docker image into the registry
	@echo "Pushing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):$(DOCKER_VERSION)"
	$(DOCKER) push $(DOCKER_NAME):$(DOCKER_VERSION)
	@echo "Pushing Docker image: $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME):latest"
	$(DOCKER) push $(DOCKER_NAME):latest
