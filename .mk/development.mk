VERSION ?= latest

##@ Development

test: install_requirements ## Test the tools-service
	pytest

test-e2e: install_requirements install_dev_requirements ## Test end-to-end the tools service (installs tools service sdk)
	pytest -s tests/e2e

lint: install_requirements ## List the tools-service
	black --check --diff --color modules tools fast_api || \
		(echo "Lint Failed. Please run 'black modules tools fast_api' to fix the issues" && exit 1)

# To run this target:
# make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
load_tools: install_requirements ## Load tools into the service
	@echo "Loading tools into blueberry-tools-service"
	./client/curl/load_tools.sh $(ARGS)

# To run this target:
# make ARGS="ClientWinMVP/json ClientWinMVP/functions/transformations.py number_str_cleanup date_transformer full_address_concat GetYear GetQuarter GetCurrency GetDealAmount identity" load_tools_json
load_tools_json: install_requirements ## Load tools into the service using json files
	@echo "Loading tools-json into blueberry-tools-service"
	./client/curl/load_tools_json.sh $(ARGS)

#stops service if running in a process
clean_slate: stop
	@echo "Clean blueberry-tools-service /tmp directory"
	+rm -rf /tmp/manifest
	+rm -rf /tmp/descriptions
	+rm -rf /tmp/files
