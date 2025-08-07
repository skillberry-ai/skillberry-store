VERSION ?= latest

##@ Development

test: install_requirements ## Test the tools-service
	pytest

test-e2e: install_dev_requirements ## Test end-to-end the tools service (installs tools service sdk)
	pytest -s blueberry_tools_service/tests/e2e

lint: install_requirements install_dev_requirements ## List the tools-service
	black --check --diff --color blueberry_tools_service/modules blueberry_tools_service/tools blueberry_tools_service/fast_api blueberry_tools_service/utils || \
		(echo "Lint Failed. Please run 'black blueberry_tools_service/modules blueberry_tools_service/tools blueberry_tools_service/fast_api blueberry_tools_service/utils' to fix the issues" && exit 1)

# To run this target:
# make ARGS="genai/transformations/client-win-functions.py GetYear GetQuarter GetCurrencySymbol ParseDealSize" load_tools
load_tools: install_requirements ## Load tools into the service
	@echo "Loading tools into blueberry-tools-service"
	./blueberry_tools_service/client/curl/load_tools.sh $(ARGS)

# To run this target:
# make ARGS="ClientWinMVP/json ClientWinMVP/functions/transformations.py number_str_cleanup date_transformer full_address_concat GetYear GetQuarter GetCurrency GetDealAmount identity" load_tools_json
load_tools_json: install_requirements ## Load tools into the service using json files
	@echo "Loading tools-json into blueberry-tools-service"
	./blueberry_tools_service/client/curl/load_tools_json.sh $(ARGS)

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

	@command -v sed >/dev/null 2>&1 || { echo "❌ 'sed' is not installed. Aborting."; exit 1; }
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Creating release with version: $(RELEASE_VERSION)"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@sleep 10
	@echo "===> Generating git tag $(RELEASE_VERSION) and creating GitHub release"
	@git checkout -b branch-$(RELEASE_VERSION)
	@echo "===> Generated release branch $(RELEASE_VERSION)"
	sed -i "s|blueberry-tools-service-sdk @ git+ssh://git@github.ibm.com/Blueberry/blueberry-sdk.git#subdirectory=blueberry_tools_service_sdk|blueberry-tools-service-sdk @ git+ssh://git@github.ibm.com/Blueberry/blueberry-sdk.git@$$RELEASE_VERSION#subdirectory=blueberry_tools_service_sdk|" pyproject.toml 
	git add pyproject.toml && \
	if git diff --cached --quiet; then \
	  		echo "!!! No updates to commit in blueberry-tools-service !!!"; \
	else \
		echo "!!! Updates detected in blueberry-tools-service, committing... !!!"; \
		git config --get user.name >/dev/null || git config user.name "Blueberry CI process" && \
		git config --get user.email >/dev/null || git config user.email "blueberry.ci@blueberry.ai" && \
		git commit -m "Update tools_service toml file with $(RELEASE_VERSION)" && \
		git push origin branch-$(RELEASE_VERSION) && \
		echo "Pushed updated toml file to blueberry-tools-service repository (origin branch-$(RELEASE_VERSION))"; \
	fi


	@git tag -a $(RELEASE_VERSION) -m "Release $(RELEASE_VERSION)" && \
	git push origin $(RELEASE_VERSION)

	#
	# Important: change to main so that later invocation of "update_git_version" properly works,
	# Note: update_git_version is called on different contexts later in this flow
	#
	@git checkout main

	#
	# The following block calls either to "basic" gh release command or an "explicit" one:
	# 
	# If no previous release exists then "basic" is called
	# If a previous release exists then "explicit" using commit range is called
	#

	@REL_PREV_RELEASE=$$(git branch -r | grep 'branch-' | sed 's|.*/branch-||' | sort -V | tail -n 2 | head -n 1); \
	if [ -z "$$REL_PREV_RELEASE" ] || [ "$$REL_PREV_RELEASE" = "$(RELEASE_VERSION)" ]; then \
		echo "No previous release found. Creating release with generated notes..."; \
		gh release create $(RELEASE_VERSION) --generate-notes; \
	else \
		echo "Previous release found: $$REL_PREV_RELEASE"; \
		REL_CURRENT_COMMIT=$$(git rev-parse --short=7 HEAD); \
		REL_PREV_COMMIT=$$(git merge-base origin/main origin/branch-$$REL_PREV_RELEASE); \
		echo "Creating release from $$REL_PREV_COMMIT to $$REL_CURRENT_COMMIT..."; \
		gh release create $(RELEASE_VERSION) --title "$(RELEASE_VERSION)" --notes "$$(git log --pretty=format:'- %s by %an' $$REL_PREV_COMMIT..$$REL_CURRENT_COMMIT)"; \
	fi



	@echo "===> Building and pushing new docker image"
	@make docker_push
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Release $(RELEASE_VERSION) created successfully"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"

update_bts_sdk: ## Update the BTS SDK
	rm -rf /tmp/blueberry-sdk || true
	@echo "==> Updating BTS SDK..."
	make docker_run
	timeout 120 bash -c 'until curl -sf http://localhost:8000/docs > /dev/null;\
 						 do echo "Waiting for Blueberry BTS service..."; sleep 5; done'
	@echo "Blueberry BTS started (using docker)"
	@cd /tmp && \
	git clone git@github.ibm.com:Blueberry/blueberry-sdk.git && \
	echo "Cloned blueberry-sdk repository into /tmp/blueberry-sdk" && \
	cd blueberry-sdk && \
	python -m venv venv && \
	source venv/bin/activate && \
	echo "Activated virtual environment" && \
	make generate_blueberry_tools_service_sdk && \
	echo "Blueberry SDK updated successfully" && \
	git add . && \
	if git diff --cached --quiet; then \
	  		echo "!!! No updates to commit in blueberry-sdk !!!"; \
	else \
		echo "!!! Updates detected in blueberry-sdk, committing... !!!"; \
		git config --get user.name >/dev/null || git config user.name "Blueberry CI process" && \
		git config --get user.email >/dev/null || git config user.email "blueberry.ci@blueberry.ai" && \
		git commit -m "Update tools_service_sdk SDK $$(date '+%Y-%m-%d %H:%M:%S')" && \
		git push origin main && \
		echo "Pushed updated SDK to blueberry-sdk repository (origin main)"; \
	fi
	make docker_stop
	echo "BTS service stopped"
	@echo "==> SDK update completed successfully"

