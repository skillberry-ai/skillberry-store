
.DEFAULT_GOAL := help

BUILD_VERSION ?= latest
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

DOCKER_REPOSITORY_NAME ?= artifactory.haifa.ibm.com:5130
IMAGE_NAME = blueberry-tools-service

DOCKER_NAME = $(DOCKER_REPOSITORY_NAME)/$(IMAGE_NAME)
DOCKER_VERSION = $(BUILD_VERSION)


TOOLS_SERVICE_SENTINEL=/tmp/tools-service.pid

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

.PHONY: help
help: ## Display this help.
	@$(AWK) 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

install_requirements: # Install requirements
ifeq ($(OS), Darwin)
	@pip install -q -r macos-requirements.txt
else
	@pip install -q -r requirements.txt
endif

install_dev_requirements: # Install dev requirements
	@pip install -q -r requirements-dev.txt

##@ Setup & teardown

run: install_requirements ## Launch the tools service
	@if [ -f $(TOOLS_SERVICE_SENTINEL) ]; then \
		echo "Blueberry Tools Service is already running"; \
	else \
		echo "Starting Blueberry Tools Service"; \
		contrib/scripts/start-service.sh /tmp/tools-service.log $(TOOLS_SERVICE_SENTINEL) python main.py; \
	fi

stop: $(TOOLS_SERVICE_SENTINEL) ## Stop the tools service
	@echo "Stopping Blueberry Tools Service"
	@contrib/scripts/stop-service.sh $(TOOLS_SERVICE_SENTINEL)

clean:  ## Clean temporary files
	@rm -f $(TOOLS_SERVICE_SENTINEL)
	-rm -rf __pycache__ .pytest_cache

##@ Docker

docker_build: ## Build docker image
	DOCKER_BUILDKIT=1 docker build --build-arg BUILD_VERSION=$(BUILD_VERSION) --build-arg BUILD_DATE="$(BUILD_DATE)" -t $(DOCKER_NAME):$(DOCKER_VERSION) .

docker_run: docker_stop ## Run the docker image
	@echo "Running Docker container: $(IMAGE_NAME)"
	docker run --name $(IMAGE_NAME) --env-file .env -d -v /var/run/docker.sock:/var/run/docker.sock -v /tmp:/tmp -p 8000:8000 $(DOCKER_NAME):$(DOCKER_VERSION)

docker_stop: ## Stop the docker image
	@echo "Stopping Docker container: $(IMAGE_NAME)"
	@docker stop $(IMAGE_NAME) > /dev/null 2>&1 || true
	@docker rm $(IMAGE_NAME) > /dev/null 2>&1 || true

# make sure that you are login with required credentials
docker_push: docker_build ## Push docker image
	docker push $(DOCKER_NAME):$(DOCKER_VERSION)

include .mk/development.mk
include .mk/ci.mk
