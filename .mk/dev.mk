# ============================================================================
# Development Tasks - Skillberry Store
# ============================================================================
# This file contains project-specific development tasks like testing and
# linting. These targets extend or override the common development targets
# from skillberry-common/.mk/dev.mk
#
# Common development targets (from skillberry-common):
#   make install-requirements  - Install Python dependencies
#   make test                  - Run unit tests
#   make help                  - Show all available commands
#
# Documentation: See docs/MAKE_SYSTEM.md for more information
# ============================================================================

##@ Development

# ----------------------------------------------------------------------------
# End-to-End Testing
# ----------------------------------------------------------------------------
# Runs comprehensive integration tests that verify the entire system works
# together. These tests may start services, make API calls, and verify
# responses.
#
# Prerequisites: Requires dev dependencies to be installed
# Usage: make test-e2e

test-e2e: ## Run end-to-end integration tests
	@echo "Installing development dependencies..."
	@$(MAKE) install-requirements ODEPS=dev
	@echo "Running end-to-end tests..."
	pytest src/skillberry_store/tests/e2e
	@echo "✓ End-to-end tests completed"

# ----------------------------------------------------------------------------
# Code Formatting and Linting
# ----------------------------------------------------------------------------
# Checks code formatting using Black (Python code formatter).
# This ensures consistent code style across the project.
#
# What it checks:
#   - Proper indentation and spacing
#   - Line length (default: 88 characters)
#   - Consistent quote usage
#   - Import ordering
#
# If this fails, run the suggested command to auto-fix formatting issues.
#
# Prerequisites: Requires dev dependencies to be installed
# Usage: make lint

lint: ## Check code formatting with Black
	@echo "Installing development dependencies..."
	@$(MAKE) install-requirements ODEPS=dev
	@echo "Checking code formatting..."
	@black --check --diff --color \
		src/skillberry_store/modules \
		src/skillberry_store/tools \
		src/skillberry_store/fast_api \
		src/skillberry_store/utils || \
		(echo "" && \
		 echo "❌ Lint check failed!" && \
		 echo "" && \
		 echo "To fix formatting issues, run:" && \
		 echo "  black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils" && \
		 echo "" && \
		 exit 1)
	@echo "✓ Code formatting is correct"

# ----------------------------------------------------------------------------
# Additional Development Targets
# ----------------------------------------------------------------------------
# Add your custom development tasks below. Examples:
#
# format: ## Auto-format code with Black
# 	black src/skillberry_store/
#
# type-check: ## Run type checking with mypy
# 	mypy src/skillberry_store/
#
# coverage: ## Run tests with coverage report
# 	pytest --cov=skillberry_store --cov-report=html
#
# docs: ## Generate documentation
# 	sphinx-build -b html docs/ docs/_build/