VERSION ?= latest

##@ CI
.PHONY: ci-pull-request
ci-pull-request: ## Executed upon ci pull_request event
	@echo "|||====> Executing make Lint"
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

.PHONY: ci-push
ci-push: ci-pull-request ## Executed upon ci push event
	@echo "|||====> Executing make docker_push (and build)"
	VERSION=$(VERSION) make docker_push
	@echo "|||====> docker_push Done."
	@echo ""
	@echo "|||====> Executing make update_sdk"
	VERSION=$(VERSION) make update_sdk
	@echo "|||====> update_sdk Done."
	@echo ""