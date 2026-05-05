# ============================================================================
# Service Lifecycle Management - Skillberry Store
# ============================================================================
# This file contains targets for managing the service lifecycle:
# starting, stopping, and cleaning up the service when running as a process.
#
# Common lifecycle targets (from skillberry-common):
#   make run   - Start the service
#   make stop  - Stop the service
#   make clean - Stop service and clean runtime data
#
# Documentation: See docs/MAKE_SYSTEM.md for more information
# ============================================================================

##@ Service Lifecycle

# ----------------------------------------------------------------------------
# Service-Specific Data Cleanup
# ----------------------------------------------------------------------------
# This target cleans up data directories specific to Skillberry Store.
# It's called automatically by 'make clean' after stopping the service.
#
# What it cleans:
#   - /tmp/manifest     - Cached manifest files
#   - /tmp/descriptions - Cached description data
#   - /tmp/files        - Temporary file storage
#
# Prerequisites: Service must be stopped first
# Usage: make clean-service-data (or just 'make clean')

clean-service-data: stop ## Clean Skillberry Store temporary data directories
	@echo "Cleaning $(SERVICE_NAME) temporary directories..."
	@rm -rf /tmp/manifest || true
	@rm -rf /tmp/descriptions || true
	@rm -rf /tmp/files || true
	@echo "✓ Service data cleaned"

# ----------------------------------------------------------------------------
# Additional Lifecycle Targets
# ----------------------------------------------------------------------------
# Add your custom lifecycle management tasks below. Examples:
#
# backup-data: ## Backup service data before cleanup
# 	@echo "Backing up service data..."
# 	@tar -czf backup-$(shell date +%Y%m%d-%H%M%S).tar.gz /tmp/manifest /tmp/descriptions
#
# reset-database: stop ## Reset database to initial state
# 	@echo "Resetting database..."
# 	@rm -f data/store.db
# 	@python scripts/init_db.py
#
# health-check: ## Check if service is running and healthy
# 	@curl -f http://localhost:8000/health || echo "Service is not responding"