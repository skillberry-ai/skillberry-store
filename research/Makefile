VERSION ?= latest
BUILD_DATE := $(shell date +%Y-%m-%d\ %H:%M)

.DEFAULT_GOAL := help

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

# Define the screen session name
SESSION_NAME=blueberry-services

BASE_DIR=$(shell pwd)

# Define commands for each of the four applications
CHATBOT_CMD="cd $(BASE_DIR)/chatbot; \
	pip install -r requirements.txt; \
	echo 'Running blueberry chatbot'; \
	streamlit run chatbot.py;"
TOOLS_SERVICE_CMD="cd $(BASE_DIR)/tools-service; \
	pip install -r requirements.txt; \
	echo 'Running brueberry tools-service'; \
	python main.py;"
TOOLS_AGENT_CMD="cd $(BASE_DIR)/tools-agent; \
	pip install -r requirements.txt; \
	echo 'Running blueberry tools-agent'; \
	python main.py;"
PROXY_CMD="cd $(BASE_DIR)/../../lite-rits/; \
	echo 'Running blueberry liteLLM proxy'; \
	litellm --config config.yaml;"
JAEGER_CMD="docker run --rm --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 14250:14250 \
  -p 14268:14268 \
  -p 14269:14269 \
  -p 9411:9411 \
  jaegertracing/all-in-one:1.66.0"


.PHONY: start stop restart

##@ Execute

start: ## Start blueberry services.
	@echo "Starting screen session: $(SESSION_NAME)"
	@screen -dmS $(SESSION_NAME)
	@screen -S $(SESSION_NAME) -X screen -t chatbot bash -c $(CHATBOT_CMD)
	@screen -S $(SESSION_NAME) -X screen -t tools-service bash -c $(TOOLS_SERVICE_CMD)
	@screen -S $(SESSION_NAME) -X screen -t tools-agent bash -c $(TOOLS_AGENT_CMD)
	@screen -S $(SESSION_NAME) -X screen -t proxy bash -c $(PROXY_CMD)
	@screen -S $(SESSION_NAME) -X screen -t jaeger bash -c $(JAEGER_CMD)
	@echo "Blueberry services started in screen session $(SESSION_NAME)"

stop: ## Stop blueberry services.
	@echo "Stopping screen session: $(SESSION_NAME)"
	@screen -S $(SESSION_NAME) -X quit || true
	@echo "Screen session $(SESSION_NAME) stopped"

restart: stop start ## Restart blueberry services.
