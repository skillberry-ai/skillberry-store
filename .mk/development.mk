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

check-git-clean:
	@changes="$$(git status --porcelain)"; \
	if [ -n "$$changes" ]; then \
	  echo "! You have uncommitted changes. Please commit, stash or clean them before releasing."; \
	  echo "=== Changes ==="; \
	  echo "$$changes"; \
	  exit 1; \
	fi

check-git-main:
	@if [ "$(shell git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
		echo "! You must be on the main branch to run this command"; \
		exit 1; \
	fi

release: check-git-main check-git-clean install_requirements  ## Release a new version
	@if [ -z "$(RELEASE_VERSION)" ]; then \
		echo "++++++++++++++++++++++++++++++++++++++++++++"; \
  		echo "RELEASE_VERSION is not set. It is required for the release"; \
  		echo "Please set RELEASE_VERSION and use 'RELEASE_VERSION=<version> make release' "; \
		echo "++++++++++++++++++++++++++++++++++++++++++++"; \
	exit 1; fi

	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Creating release with version: $(RELEASE_VERSION)"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@sleep 10
	@echo "===> Generating git tag $(RELEASE_VERSION) and creating GitHub release"
	@git tag -a $(RELEASE_VERSION) -m "Release $(RELEASE_VERSION)" && \
	git push origin $(RELEASE_VERSION) && \
	gh release create $(RELEASE_VERSION) --generate-notes

	@echo "===> Building and pushing new docker image"
	@make docker_push
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Release $(RELEASE_VERSION) created successfully"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
