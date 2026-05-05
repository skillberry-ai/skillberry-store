# ============================================================================
# Development Targets - Project-Specific Overrides
# ============================================================================
# This file contains development targets specific to Skillberry Store.
# The main Makefile provides standard targets (test, lint, install, etc.)
# Use this file to add or override project-specific development workflows.
#
# For detailed documentation, see: docs/MAKE_SYSTEM.md
# ============================================================================

##@ Development (Project-Specific)

# ============================================================================
# End-to-End Testing
# ============================================================================
# Override the default test-e2e target to install dev dependencies first
test-e2e: ## Run end-to-end tests (installs SDK)
	@echo "Installing development dependencies..."
	@$(MAKE) install ODEPS=dev
	@echo "Running end-to-end tests..."
	@pytest src/skillberry_store/tests/e2e
	@echo "✓ End-to-end tests completed"

# ============================================================================
# Code Linting
# ============================================================================
# Override the default lint target with project-specific paths
lint: ## Lint the Skillberry Store codebase
	@echo "Installing development dependencies..."
	@$(MAKE) install ODEPS=dev
	@echo "Checking code formatting..."
	@black --check --diff --color \
		src/skillberry_store/modules \
		src/skillberry_store/tools \
		src/skillberry_store/fast_api \
		src/skillberry_store/utils || \
		(echo "❌ Lint failed. Run 'make format' to fix issues" && exit 1)
	@echo "✓ Code formatting is correct"

# ============================================================================
# Additional Development Targets
# ============================================================================
# Add any project-specific development targets below
# Examples:
#   - Custom test suites
#   - Code generation
#   - Database migrations
#   - Documentation generation
# ============================================================================

# Example: Run specific test suite
# .PHONY: test-integration
# test-integration: install
# 	@pytest src/skillberry_store/tests/integration

# Example: Generate documentation
# .PHONY: docs
# docs: install
# 	@sphinx-build -b html docs/ docs/_build/

# ============================================================================
# Notes
# ============================================================================
# - Keep this file focused on development workflows
# - Use clear, descriptive target names
# - Add comments explaining what each target does
# - Follow the pattern: target: dependencies ## Description
# ============================================================================