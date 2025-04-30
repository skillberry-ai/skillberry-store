VERSION ?= latest

##@ CI
.PHONY: ci_pull_request
ci_pull_request: ## Executed upon ci pull_request event
	@echo "|||====> Executing make Lint"
	VERSION=$(VERSION) make lint
	@echo "|||====> make lint Done."
	@echo ""
	@echo "|||====> Executing make test"
	VERSION=$(VERSION) make test
	@echo "|||====> make test Done."
	@echo ""

.PHONY: ci_push
ci_push: ci_pull_request ## Executed upon ci push event
	@echo "|||====> Executing make test-e2e"
	VERSION=$(VERSION) make test-e2e
	@echo "|||====> make test-e2e Done."
	@echo ""
	@echo "|||====> Executing make docker_build"
	VERSION=$(VERSION) make docker_build
	@echo "|||====> docker_build Done."
	@echo ""
	@echo "|||====> Executing make docker_push"
	VERSION=$(VERSION) make docker_push
	@echo "|||====> docker_push Done."
	@echo ""
