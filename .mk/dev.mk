##@ Development

test-e2e: ## Test end-to-end the tools service (installs sdk)
	@$(MAKE) install-requirements ODEPS=dev
	pytest -s src/skillberry_store/tests/e2e

lint: ## List the tools-service
	@$(MAKE) install-requirements ODEPS=dev
	black --check --diff --color src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils || \
		(echo "Lint Failed. Please run 'black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils' to fix the issues" && exit 1)

