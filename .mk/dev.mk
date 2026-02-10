##@ Development

test-e2e: ## Test end-to-end the tools service (installs sdk)
	@$(MAKE) install_requirements ODEPS=dev
	pytest -s src/skillberry_store/tests/e2e

lint: ## List the tools-service
	@$(MAKE) install_requirements ODEPS=dev
	black --check --diff --color src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils || \
		(echo "Lint Failed. Please run 'black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils' to fix the issues" && exit 1)

# To run this target:
# make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
load_tools: install_requirements ## Load tools into the service
	@echo "Loading tools into $(SERVICE_NAME)"
	./skillberry_store/client/curl/load_tools.sh $(ARGS)

# To run this target:
# make ARGS="ClientWinMVP/json ClientWinMVP/functions/transformations.py number_str_cleanup date_transformer full_address_concat GetYear GetQuarter GetCurrency GetDealAmount identity" load_tools_json
load_tools_json: install_requirements ## Load tools into the service using json files
	@echo "Loading tools-json into $(SERVICE_NAME)"
	./skillberry_store/client/curl/load_tools_json.sh $(ARGS)

