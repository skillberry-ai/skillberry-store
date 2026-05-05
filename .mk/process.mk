# ============================================================================
# Service Lifecycle Targets - Project-Specific Overrides
# ============================================================================
# This file contains service lifecycle targets specific to Skillberry Store.
# The main Makefile provides standard targets (run, stop, clean, etc.)
# Use this file to add or override project-specific lifecycle operations.
#
# For detailed documentation, see: docs/MAKE_SYSTEM.md
# ============================================================================

##@ Service Lifecycle (Project-Specific)

# ============================================================================
# Service Data Cleanup
# ============================================================================
# Override the default clean-service-data target with project-specific cleanup
clean-service-data: stop ## Clean Skillberry Store specific data directories
	@echo "Cleaning $(SERVICE_NAME) data directories..."
	@rm -rf /tmp/manifest
	@rm -rf /tmp/descriptions
	@rm -rf /tmp/files
	@echo "✓ Service data cleaned"

# ============================================================================
# Additional Lifecycle Targets
# ============================================================================
# Add any project-specific lifecycle targets below
# Examples:
#   - Database initialization
#   - Cache warming
#   - Health checks
#   - Backup operations
# ============================================================================

# Example: Initialize service data
# .PHONY: init-data
# init-data:
# 	@echo "Initializing service data..."
# 	@mkdir -p /tmp/manifest /tmp/descriptions /tmp/files
# 	@echo "✓ Data directories created"

# Example: Health check
# .PHONY: health-check
# health-check:
# 	@echo "Checking service health..."
# 	@curl -sf http://$(SERVICE_HOST):$(MAIN_SERVICE_PORT)/health || \
# 		(echo "❌ Service is not healthy" && exit 1)
# 	@echo "✓ Service is healthy"

# ============================================================================
# Notes
# ============================================================================
# - Keep this file focused on service lifecycle operations
# - Use clear, descriptive target names
# - Add comments explaining what each target does
# - Follow the pattern: target: dependencies ## Description
# - Consider idempotency (targets should be safe to run multiple times)
# ============================================================================