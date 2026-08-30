##@ Development

lint: ## List the tools-service
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
# ACL mode is baked into the bundle at build time by vite.config.ts, so the
# access-control config is a build input too — mirror its path resolution
# here. Wildcard-guarded: an absent config is a supported setup (both
# vite.config.ts and load_config() fall back to mode=disabled), so it must
# not become a hard "No rule to make target" failure.
ACL_CONFIG  := $(wildcard $(or $(SBS_ACCESS_CONTROL_CONFIG),access_control_config.yaml))

.PHONY: ui-build ui-clean ui-dev ui-typecheck ui-test
ui-build: $(UI_STAMP) ## Build the UI static bundle (idempotent, stamp-based)

# Bundle only — no `tsc` prefix. Vite/esbuild strips types without checking,
# which matches how `npx vite` (dev) and `vitest` have always run. Type
# checking is a separate concern; use `make ui-typecheck` as a CI gate.
$(UI_STAMP): $(UI_SOURCES) $(UI_NM_STAMP) $(ACL_CONFIG)
	@echo "===> Building UI static bundle"
	@cd $(UI_DIR) && npx vite build
	@mkdir -p .stamps && touch $@

ui-typecheck: $(UI_NM_STAMP) ## Run TypeScript type checking on the UI (not part of ui-build)
	@cd $(UI_DIR) && npm run typecheck

# The vitest suite is not part of `make test` (pytest-only, and it must run
# without a node toolchain) and no CI workflow runs it, which is how several
# assertions rotted unnoticed. NOTE: the suite currently has pre-existing
# failures unrelated to the /api normalisation work (VMCPServerDetailPage*,
# SkillsPage.cascade-delete, AnthropicSkillImporter, openApiGenerator.error), so
# this is a developer tool, not yet a green gate. The invariant that matters at
# runtime — no dead "/api" URL prefix ever reaching fetch() — is guarded
# statically by src/skillberry_store/tests/test_ui_api_prefix.py, which DOES run
# in `make test`. Pass UI_TEST_ARGS to scope the run:
#   make ui-test UI_TEST_ARGS=src/utils/endpoints.test.ts
UI_TEST_ARGS ?=
ui-test: $(UI_NM_STAMP) ## Run the UI unit tests (vitest; UI_TEST_ARGS to scope, see note)
	@cd $(UI_DIR) && npx vitest run $(UI_TEST_ARGS)

$(UI_NM_STAMP): $(UI_DIR)/package.json $(UI_DIR)/package-lock.json
	@echo "===> Installing UI dependencies"
	@cd $(UI_DIR) && (test -d node_modules || npm ci)
	@mkdir -p .stamps && touch $@

ui-clean: ## Remove UI build artifacts and node_modules
	rm -rf $(UI_DIST) $(UI_STAMP) $(UI_NM_STAMP) $(UI_DIR)/node_modules

ui-dev: $(UI_NM_STAMP) ## Run the Vite dev server with HMR (uses file watchers)
	@cd $(UI_DIR) && npx vite --host 0.0.0.0 --port $${VITE_UI_PORT:-8002}


##@ Docker image variants

# The default image is core-only (Dockerfile sets ARG PLUGIN_EXTRAS= empty).
# This builds the companion variant carrying every bundled plugin, tagged
# :<version>-full / :latest-full so both can coexist in the registry. Run it
# with `make docker-run IMAGE_TAG_SUFFIX=-full`.
.PHONY: docker-build-full
docker-build-full: ## Build the all-plugins image variant (tagged -full)
	@$(MAKE) docker-build \
		IMAGE_TAG_SUFFIX=-full \
		EXTRA_BUILD_ARGS='--build-arg PLUGIN_EXTRAS=plugins-all'
