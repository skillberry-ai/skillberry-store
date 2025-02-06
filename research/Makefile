# Define the screen session name
SESSION_NAME=blueberry-services

BASE_DIR=$(shell pwd)

# Define commands for each of the four applications
CHATBOT_CMD="cd $(BASE_DIR)/chatbot; \
	pip install -r requierments; \
	echo 'Running blueberry chatbot'; \
	streamlit run chatbot.py;"
TOOLS_SERVICE_CMD="cd $(BASE_DIR)/tools-service; \
	pip install -r requierments; \
	echo 'Running blueberry tools-service'; \
	python main.py;"
TOOLS_AGENT_CMD="cd $(BASE_DIR)/tools-agent; \
	pip install -r requierments; \
	echo 'Running blueberry tools-agent'; \
	python main.py;"
PROXY_CMD="cd $(BASE_DIR)/../../lite-rits/; \
	pip install -r requierments; \
	echo 'Running blueberry liteLLM proxy'; \
	litellm --config config.yaml;"

.PHONY: start stop restart

start:
	@echo "Starting screen session: $(SESSION_NAME)"
	@screen -dmS $(SESSION_NAME)
	@screen -S $(SESSION_NAME) -X screen -t chatbot bash -c $(CHATBOT_CMD)
	@screen -S $(SESSION_NAME) -X screen -t tools-service bash -c $(TOOLS_SERVICE_CMD)
	@screen -S $(SESSION_NAME) -X screen -t tools-agent bash -c $(TOOLS_AGENT_CMD)
	@screen -S $(SESSION_NAME) -X screen -t proxy bash -c $(PROXY_CMD)
	@echo "Blueberry services started in screen session $(SESSION_NAME)"

stop:
	@echo "Stopping screen session: $(SESSION_NAME)"
	@screen -S $(SESSION_NAME) -X quit || true
	@echo "Screen session $(SESSION_NAME) stopped"

restart: stop start