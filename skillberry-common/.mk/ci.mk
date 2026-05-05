# =============================================================================
# CI/CD Targets
# =============================================================================
# This file contains targets used by Continuous Integration and Continuous
# Deployment pipelines. These targets orchestrate multiple checks and builds.
#
# Key targets:
#   - ci-pull-request: Run all checks for pull requests
#   - ci-push: Run all checks for pushes to main branch
#
# These targets are typically called by GitHub Actions or other CI systems.
# =============================================================================

# Version can be overridden by CI system (defaults to "latest")
VERSION ?= latest

##@ CI

# -----------------------------------------------------------------------------
# Pull Request Checks
# -----------------------------------------------------------------------------
# Run all validation checks for pull requests
# This ensures code quality before merging
.PHONY: ci-pull-request
ci-pull-request: ## Executed upon ci pull_request event
	@echo "|||====> Executing make lint"
	VERSION=$(VERSION) make lint
	@echo "|||====> make lint Done."
	@echo ""
	@echo "|||====> Executing make test"
	VERSION=$(VERSION) make test
	@echo "|||====> make test Done."
	@echo ""
	@echo "|||====> Executing make test-e2e"
	VERSION=$(VERSION) make test-e2e
	@echo "|||====> make test-e2e Done."
	@echo ""

# -----------------------------------------------------------------------------
# Push Checks
# -----------------------------------------------------------------------------
# Run all checks for pushes to main branch
# This includes PR checks plus Docker build and SDK update
.PHONY: ci-push
ci-push: ci-pull-request ## Executed upon ci push event
	@echo "|||====> Executing make docker-push (and build)"
	VERSION=$(VERSION) make docker-push
	@echo "|||====> docker-push Done."
	@echo ""
	@echo "|||====> Executing make update-sdk"
	VERSION=$(VERSION) make update-sdk
	@echo "|||====> update-sdk Done."
	@echo ""
