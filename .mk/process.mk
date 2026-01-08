##@ Setup & teardown as a process

SERVICE_SENTINEL=/tmp/$(SERVICE_NAME)-service.pid
SERVICE_LOG=/tmp/$(SERVICE_NAME).log

.PHONY: run stop clean clean_service_data

run: install_requirements ## Run the service (idempotent)
	@if [ -f $(SERVICE_SENTINEL) ]; then \
		echo "$(SERVICE_NAME) service is already running. Check the SERVICE_SENTINEL file ($(SERVICE_SENTINEL))"; \
	else \
		rc=0; \
		echo "Starting $(SERVICE_NAME) Service"; \
		$(SB_COMMON_PATH)/scripts/start-service.sh $(SERVICE_LOG) $(SERVICE_SENTINEL) python -m $(SERVICE_ENTRY_MODULE) || rc=$$?; \
		echo "Service $(SERVICE_NAME) terminated with exit code: $$rc" ; \
	fi

stop: ## Stop the service (idempotent)
	@if [ -f $(SERVICE_SENTINEL) ]; then \
		echo "Stopping $(SERVICE_NAME) Service"; \
		$(SB_COMMON_PATH)/scripts/stop-service.sh $(SERVICE_SENTINEL); \
	else \
		echo "$(SERVICE_NAME) service is already stopped. Missing SERVICE_SENTINEL file ($(SERVICE_SENTINEL))"; \
	fi

clean: stop clean_service_data	## Clean all runtime data (stopped service)
	@rm -f $(SERVICE_SENTINEL)
	@rm -f $(SERVICE_LOG)
	-rm -rf __pycache__ .pytest_cache
	rm -rf build dist *.egg-info	

# clean_service_data is unimplemented, because it is service-specific

