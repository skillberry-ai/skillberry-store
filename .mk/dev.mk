##@ Development

test-e2e: install_dev_requirements ## Test end-to-end the tools service (installs sdk)
	pytest -s skillberry_store/tests/e2e

lint: install_requirements install_dev_requirements ## List the tools-service
	black --check --diff --color skillberry_store/modules skillberry_store/tools skillberry_store/fast_api skillberry_store/utils || \
		(echo "Lint Failed. Please run 'black skillberry_store/modules skillberry_store/tools skillberry_store/fast_api skillberry_store/utils' to fix the issues" && exit 1)

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
	sed -i "s|skillberry-store-sdk @ git+ssh://git@github.ibm.com/skillberry/skillberry-store-sdk.git#subdirectory=skillberry_store_sdk|skillberry-store-sdk @ git+ssh://git@github.ibm.com/skillberry/skillberry-store-sdk.git@$$RELEASE_VERSION#subdirectory=skillberry_store_sdk|" pyproject.toml 
	git add pyproject.toml && \
	if git diff --cached --quiet; then \
	  		echo "!!! No updates to commit in skillberry-store !!!"; \
	else \
		echo "!!! Updates detected in skillberry-store, committing... !!!"; \
		git config --get user.name >/dev/null || git config user.name "Skillberry CI process" && \
		git config --get user.email >/dev/null || git config user.email "skillberry.ci@skillberry.ai" && \
		git commit -m "Update tools_service toml file with $(RELEASE_VERSION)" && \
		git push origin branch-$(RELEASE_VERSION) && \
		echo "Pushed updated toml file to skillberry-store repository (origin branch-$(RELEASE_VERSION))"; \
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


	#
	# Important: change back to release branch so that docker image is built with customized
	# toml/requirement files
	#
	@git checkout branch-$(RELEASE_VERSION)


	@echo "===> Building and pushing new docker image"
	@make docker_push
	@echo "++++++++++++++++++++++++++++++++++++++++++++"
	@echo "=> Release $(RELEASE_VERSION) created successfully"
	@echo "++++++++++++++++++++++++++++++++++++++++++++"

update_bts_sdk: ## Update the SBS SDK
	rm -rf /tmp/skillberry-store-sdk || true
	@echo "==> Updating SBS SDK..."
	make docker_run
	timeout 120 bash -c 'until curl -sf http://localhost:8000/docs > /dev/null;\
 						 do echo "Waiting for Skillberry SBS service..."; sleep 5; done'
	@echo "Skillberry SBS started (using docker)"
	@cd /tmp && \
	git clone git@github.ibm.com:skillberry/skillberry-store-sdk.git && \
	echo "Cloned skillberry-store-sdk repository into /tmp/skillberry-store-sdk" && \
	cd skillberry-store-sdk && \
	python -m venv venv && \
	source venv/bin/activate && \
	echo "Activated virtual environment" && \
	make generate_skillberry_store_sdk && \
	echo "Skillberry Store SDK updated successfully" && \
	git add . && \
	if git diff --cached --quiet; then \
	  		echo "!!! No updates to commit in skillberry-store-sdk !!!"; \
	else \
		echo "!!! Updates detected in skillberry-store-sdk, committing... !!!"; \
		git config --get user.name >/dev/null || git config user.name "Skillberry CI process" && \
		git config --get user.email >/dev/null || git config user.email "skillberry.ci@skillberry.ai" && \
		git commit -m "Update tools_service_sdk SDK $$(date '+%Y-%m-%d %H:%M:%S')" && \
		git push origin main && \
		echo "Pushed updated SDK to skillberry-store-sdk repository (origin main)"; \
	fi
	make docker_stop
	echo "SBS service stopped"
	@echo "==> SDK update completed successfully"

