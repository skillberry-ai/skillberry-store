
.DEFAULT_GOAL := help

BUILD_VERSION ?= latest
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

DOCKER_NAME = blueberry-tools-service
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

install_requirements: # Install dependencies
ifeq ($(OS), Darwin)
	@pip install -q -r macos-requirements.txt
else
	@pip install -q -r requirements.txt
endif

##@ Setup & teardown

run: install_requirements ## Launch the tools service
	@if [ -f $(TOOLS_SERVICE_SENTINEL) ]; then \
		echo "Blueberry Tools Service is already running"; \
	else \
		echo "Starting Blueberry Tools Service"; \
		contrib/scripts/start-service.sh /tmp/tools-service.log $(TOOLS_SERVICE_SENTINEL) python main.py; \
	fi	

test: install_requirements ## Test the application
	pytest

## Use only when absolutely needed! (e.g., initial setup or when service API changed)
gen_client: $(TOOLS_SERVICE_SENTINEL)
	@mkdir -p client/gen
	@rm -fr client/gen/*
	@openapi-generator-cli generate -i http://0.0.0.0:8000/openapi.json -g python -o client/gen --skip-validate-spec
	@pip install --upgrade client/gen

stop: $(TOOLS_SERVICE_SENTINEL)
	@echo "Stopping Blueberry Tools Service"
	@contrib/scripts/stop-service.sh $(TOOLS_SERVICE_SENTINEL)

clean:  ## Clean temporary files
	@rm -f $(TOOLS_SERVICE_SENTINEL)
	-rm -rf __pycache__ .pytest_cache

##@ Docker

docker_build: ## build  docker image
	docker build --build-arg BUILD_VERSION=$(BUILD_VERSION) --build-arg BUILD_DATE="$(BUILD_DATE)" -t $(DOCKER_NAME):$(DOCKER_VERSION) .

docker_stop: ## stop docker
	@echo "Stopping Docker container: $(DOCKER_NAME)"
	@docker stop $(DOCKER_NAME) > /dev/null 2>&1 || true
	@docker rm $(DOCKER_NAME) > /dev/null 2>&1 || true

docker_run: docker_stop ## run the docker image
	@echo "Running Docker container: $(DOCKER_NAME)"
	docker run --name $(DOCKER_NAME) -d -v /tmp:/tmp -p 8000:8000 $(DOCKER_NAME):$(DOCKER_VERSION)

# To run this target: 
# make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
load_tools: ## Load tools into the service
	@echo "Loading tools into blueberry-tools-service"
	./client/curl/load_tools.sh $(ARGS) 

clean_slate: stop docker_stop 
	@echo "Cleaning slate blueberry-tools-service"
	+rm -rf /tmp/manifest
	+rm -rf /tmp/descriptions
	+rm -rf /tmp/files

