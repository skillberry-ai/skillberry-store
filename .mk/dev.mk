# =============================================================================
# Project-Specific Development Targets - Skillberry Store
# =============================================================================
# This file contains development targets specific to the Skillberry Store project.
# These targets extend the common development targets from skillberry-common.
#
# Common targets (from skillberry-common/.mk/dev.mk) include:
#   - install-requirements: Install Python dependencies
#   - test: Run unit tests
#   - release: Create a new release
#   - update-sdk: Generate Python SDK from OpenAPI spec
#
# See docs/MAKE_SYSTEM.md for complete documentation.
# =============================================================================

##@ Development

# -----------------------------------------------------------------------------
# End-to-End Testing
# -----------------------------------------------------------------------------
# Run comprehensive end-to-end tests that verify the entire service workflow
# This includes testing the tools service with SDK installation
test-e2e: ## Test end-to-end the tools service (installs sdk)
	@$(MAKE) install-requirements ODEPS=dev
	pytest src/skillberry_store/tests/e2e

# -----------------------------------------------------------------------------
# Code Quality
# -----------------------------------------------------------------------------
# Check code formatting using Black formatter
# This target will fail if any formatting issues are found
# To fix issues, run: black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils
lint: ## Lint the tools-service
	@$(MAKE) install-requirements ODEPS=dev
	black --check --diff --color src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils || \
		(echo "Lint Failed. Please run 'black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils' to fix the issues" && exit 1)