# =============================================================================
# Common Repository Operations
# =============================================================================
# This file contains targets for managing the skillberry-common subtree.
# The subtree allows sharing common Make targets across multiple projects.
#
# Key targets:
#   - fetch-common: Fetch updates from skillberry-common repo
#   - status-common: Show local changes not yet pushed upstream
#   - pull-common: Pull updates from skillberry-common into project
#   - split-common: Create PR branch for contributing changes back
#
# Subtree workflow:
# 1. Make changes to files in skillberry-common/
# 2. Test changes in your project
# 3. Use split-common to create a PR branch
# 4. Submit PR to skillberry-common repository
# 5. After merge, use pull-common to get updates in other projects
# =============================================================================

##@ Common repository operations

# -----------------------------------------------------------------------------
# Fetch Updates
# -----------------------------------------------------------------------------
# Fetch the latest commits from the skillberry-common repository
# This doesn't modify your local files, just updates git's knowledge
fetch-common:	## Fetch from common repo
	@echo "Fetching common content from $(SB_COMMON_REMOTE)"
	@git fetch $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH)

# -----------------------------------------------------------------------------
# Status Check
# -----------------------------------------------------------------------------
# Show which local commits in skillberry-common haven't been pushed upstream
# This helps you see what changes you've made that could be contributed back
status-common:	## Status of local common commits compared to common HEAD
	@echo "Computing delta of common from $(SB_COMMON_REMOTE)"
	@$(SB_COMMON_PATH)/scripts/subtree-delta.sh $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) $(SB_COMMON_PATH)

# -----------------------------------------------------------------------------
# Pull Updates
# -----------------------------------------------------------------------------
# Pull updates from skillberry-common repository into your project
# This merges upstream changes into your local skillberry-common directory
pull-common:	## Pull from common repo to local common folder
	@echo "Pulling common content from $(SB_COMMON_REMOTE)"
	@git subtree pull --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) -m "Pull from $(SB_COMMON_REMOTE)"

# -----------------------------------------------------------------------------
# Push Updates (Not Recommended)
# -----------------------------------------------------------------------------
# Direct push of local changes to skillberry-common repository
# WARNING: This is not recommended. Use split-common instead to create a PR
push-common:	## Direct push local commits in common folder to common repo - NOT RECOMMENDED
	@echo "Pushing common update to $(SB_COMMON_REMOTE)"
	@git subtree push --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) --rejoin

# -----------------------------------------------------------------------------
# Create PR Branch
# -----------------------------------------------------------------------------
# Split your local skillberry-common changes into a separate branch
# This creates a branch suitable for submitting a pull request
# 
# Usage:
#   make split-common              # Create PR branch
#   make split-common REPLACE=y    # Override existing PR branch
split-common:	## Split a common-only branch to PR back to common repo (+REPLACE=y to override)
	@echo "Creating PR branch for common repo from local commits"
	@$(SB_COMMON_PATH)/scripts/split-common.sh $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) $(SB_COMMON_PATH) $(REPLACE)