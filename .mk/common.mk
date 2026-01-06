##@ Common repository operations

fetch-common:	## Fetch from common repo
	@echo "Fetching common content from $(SB_COMMON_REMOTE)"
	@git fetch $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH)

status-common:	## Status of local common commits compared to common HEAD
	@echo "Computing delta of common from $(SB_COMMON_REMOTE)"
	@$(SB_COMMON_PATH)/scripts/subtree-delta.sh $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) $(SB_COMMON_PATH)

pull-common:	## Pull from common repo to local common folder
	@echo "Pulling common content from $(SB_COMMON_REMOTE)"
	@git subtree pull --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) -m "Pull from $(SB_COMMON_REMOTE)"

push-common:	## Push local commits in common folder to common repo - NOT RECOMMENDED
	@echo "Pushing common update to $(SB_COMMON_REMOTE)"
	@git subtree push --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH)

pr-common:		## Create a PR for common repo based on local changes in common folder
    @SB_COMMON_REMOTE='$(SB_COMMON_REMOTE)' \
      SB_COMMON_BRANCH='$(SB_COMMON_BRANCH)' \
      SB_COMMON_PATH='$(SB_COMMON_PATH)' \
      $(SB_COMMON_PATH)/scripts/make-pr-common.sh
