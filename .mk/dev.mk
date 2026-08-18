##@ Development

lint: ## Lint the codebase
	@$(MAKE) install-requirements ODEPS=dev
	black --check --diff --color src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils || \
		(echo "Lint Failed. Please run 'black src/skillberry_store/modules src/skillberry_store/tools src/skillberry_store/fast_api src/skillberry_store/utils' to fix the issues" && exit 1)

##@ UI

UI_DIR      := src/skillberry_store/ui
UI_DIST     := $(UI_DIR)/dist
UI_STAMP    := .stamps/ui-build
UI_NM_STAMP := .stamps/ui-node-modules
# Inputs that invalidate the built bundle.
UI_SOURCES  := $(shell find $(UI_DIR)/src -type f 2>/dev/null) \
               $(UI_DIR)/index.html \
               $(UI_DIR)/vite.config.ts \
               $(UI_DIR)/tsconfig.json \
               $(UI_DIR)/tsconfig.node.json

.PHONY: ui-build ui-clean ui-dev ui-typecheck
ui-build: $(UI_STAMP) ## Build the UI static bundle (idempotent, stamp-based)

# Bundle only — no `tsc` prefix. Vite/esbuild strips types without checking,
# which matches how `npx vite` (dev) and `vitest` have always run. Type
# checking is a separate concern; use `make ui-typecheck` as a CI gate.
$(UI_STAMP): $(UI_SOURCES) $(UI_NM_STAMP)
	@echo "===> Building UI static bundle"
	@cd $(UI_DIR) && npx vite build
	@mkdir -p .stamps && touch $@

ui-typecheck: $(UI_NM_STAMP) ## Run TypeScript type checking on the UI (not part of ui-build)
	@cd $(UI_DIR) && npm run typecheck

$(UI_NM_STAMP): $(UI_DIR)/package.json $(UI_DIR)/package-lock.json
	@echo "===> Installing UI dependencies"
	@cd $(UI_DIR) && (test -d node_modules || npm ci)
	@mkdir -p .stamps && touch $@

ui-clean: ## Remove UI build artifacts and node_modules
	rm -rf $(UI_DIST) $(UI_STAMP) $(UI_NM_STAMP) $(UI_DIR)/node_modules

ui-dev: $(UI_NM_STAMP) ## Run the Vite dev server with HMR (uses file watchers)
	@cd $(UI_DIR) && npx vite --host 0.0.0.0 --port $${VITE_UI_PORT:-8002}

