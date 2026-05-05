# =============================================================================
# Process Management Targets
# =============================================================================
# This file contains targets for managing the service as a local process.
# These targets handle starting, stopping, and cleaning up the service.
#
# Key targets:
#   - run: Start the service as a background process
#   - stop: Stop the running service gracefully
#   - clean: Stop service and remove all runtime files
#   - clean-service-data: Project-specific data cleanup (override in project)
#
# Process tracking:
#   - PID file: /tmp/<service-name>-service.pid
#   - Log file: /tmp/<service-name>.log
# =============================================================================

##@ Setup & teardown as a process

# -----------------------------------------------------------------------------
# File Locations
# -----------------------------------------------------------------------------
# Sentinel file that stores the process ID of the running service
# Used to track and manage the service process
SERVICE_SENTINEL=/tmp/$(SERVICE_NAME)-service.pid

# Log file where service output is written
# Use 'tail -f' on this file to monitor the service
SERVICE_LOG=/tmp/$(SERVICE_NAME).log

# -----------------------------------------------------------------------------
# Target Declarations
# -----------------------------------------------------------------------------
.PHONY: run stop clean clean_service_data

# -----------------------------------------------------------------------------
# Dependency Configuration
# -----------------------------------------------------------------------------
# Determine which dependencies are needed based on LLM service usage
# If USE_LLM_SVCS=1, we need to check for Watson/RITS credentials
ifeq ($(USE_LLM_SVCS),1)
  RUN_DEPS := install-requirements check-rits-watsonx-envs .stamps/srv.env
else
  RUN_DEPS := install-requirements .stamps/srv.env
endif

# -----------------------------------------------------------------------------
# Service Lifecycle
# -----------------------------------------------------------------------------
# Start the service as a background process
# This target is idempotent - running it multiple times won't start multiple instances
run: $(RUN_DEPS) ## Run the service (idempotent)
	@if [ -f $(SERVICE_SENTINEL) ]; then \
		echo "$(SERVICE_NAME) service is already running. Check the SERVICE_SENTINEL file ($(SERVICE_SENTINEL))"; \
	else \
		set -a; source .stamps/srv.env; set +a; \
		rc=0; \
		echo "Starting $(SERVICE_NAME) service (version $(BUILD_VERSION) built on $(BUILD_DATE))"; \
		$(SB_COMMON_PATH)/scripts/start-service.sh $(SERVICE_LOG) $(SERVICE_SENTINEL) python -m $(SERVICE_ENTRY_MODULE) || rc=$$?; \
		echo "Service $(SERVICE_NAME) terminated with exit code: $$rc" ; \
	fi

# Stop the running service gracefully
# This target is idempotent - safe to run even if service is not running
stop: ## Stop the service (idempotent)
	@if [ -f $(SERVICE_SENTINEL) ]; then \
		echo "Stopping $(SERVICE_NAME) Service"; \
		$(SB_COMMON_PATH)/scripts/stop-service.sh $(SERVICE_SENTINEL); \
	else \
		echo "$(SERVICE_NAME) service is already stopped. Missing SERVICE_SENTINEL file ($(SERVICE_SENTINEL))"; \
	fi

# Clean up all runtime files and artifacts
# This stops the service first, then removes all generated files
clean: stop clean-service-data	## Clean all runtime data (stopped service)
	@rm -f $(SERVICE_SENTINEL)
	@rm -f $(SERVICE_LOG)
	-rm -rf __pycache__ .pytest_cache
	rm -rf build dist *.egg-info	

# -----------------------------------------------------------------------------
# Service-Specific Data Cleanup
# -----------------------------------------------------------------------------
# This target should be overridden in the project's .mk/process.mk file
# to clean up any service-specific data directories or files
# 
# Example override in project's .mk/process.mk:
#   clean-service-data: stop
#       @echo "Cleaning service data"
#       rm -rf /tmp/my-service-data
#
# Default implementation does nothing (projects must override if needed)
# clean_service_data is unimplemented by default - override in project .mk files