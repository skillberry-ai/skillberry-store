##@ Setup & teardown as a process

.PHONY: run stop clean clean_service_data

run: install_requirements ## Run the service
	@if [ -f $(SERVICE_SENTINEL) ]; then \
		echo "Blueberry Tools Service is already running. Check the TOOLS_SERVICE_SENTINEL file (default /tmp/tools-service.pid)"; \
	else \
		echo "Starting $(SERVICE_NAME) Service"; \
		$(SB_COMMON_PATH)/scripts/start-service.sh /tmp/$(SERVICE_NAME).log $(SERVICE_SENTINEL) python -m $(SERVICE_ENTRY_MODULE); \
	fi

stop: $(SERVICE_SENTINEL) ## Stop the service
	@echo "Stopping Blueberry Tools Service"
	@$(SB_COMMON_PATH)/scripts/stop-service.sh $(TOOLS_SERVICE_SENTINEL)

clean: clean_service_data
	@rm -f $(SERVICE_SENTINEL)
	-rm -rf __pycache__ .pytest_cache
	rm -rf build dist *.egg-info	
	$(MAKE) clean_service_data

clean_service_data:	stop ## Clean service-specific data - override in your service local.mk if needed
	@echo "No service-specific data to remove"

