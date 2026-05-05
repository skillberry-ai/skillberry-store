# =============================================================================
# Project-Specific Process Management - Skillberry Store
# =============================================================================
# This file contains process management targets specific to the Skillberry Store.
# These targets extend the common process targets from skillberry-common/.mk/process.mk.
#
# Common targets (from skillberry-common/.mk/process.mk) include:
#   - run: Start the service as a background process
#   - stop: Stop the running service
#   - clean: Stop service and clean up runtime files
#
# See docs/MAKE_SYSTEM.md for complete documentation.
# =============================================================================

##@ Setup & teardown as a process

# -----------------------------------------------------------------------------
# Service Data Cleanup
# -----------------------------------------------------------------------------
# Clean service-specific data directories
# This target is called by 'make clean' after stopping the service
clean-service-data: stop
	@echo "Clean $(SERVICE_NAME) /tmp directory"
	+rm -rf /tmp/manifest
	+rm -rf /tmp/descriptions
	+rm -rf /tmp/files