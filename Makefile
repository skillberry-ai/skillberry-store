# Root Makefile for Skillberry Store.
#
# Project-specific settings live in .mk/local.mk.
# Shared targets and defaults are provided by the vendored
# skillberry-common subtree under $(SB_COMMON_PATH).

SB_COMMON_REPO ?= git@github.com:skillberry-ai/skillberry-common.git
SB_COMMON_BRANCH ?= main
SB_COMMON_REMOTE ?= skillberry-common
SB_COMMON_PATH ?= skillberry-common

include .mk/local.mk
include $(SB_COMMON_PATH)/Makefile

# Bootstrap the vendored shared makefiles if the subtree is missing.
$(SB_COMMON_PATH)/Makefile:
	@echo "Adding $(SB_COMMON_REMOTE) under relative path $(SB_COMMON_PATH)"
	@if ! git remote | grep -Fxq "$(SB_COMMON_REMOTE)"; then \
		echo "$(SB_COMMON_REMOTE) remote does not exist - adding it"; \
		git remote add "$(SB_COMMON_REMOTE)" "$(SB_COMMON_REPO)"; \
	fi
	@git subtree add --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH)