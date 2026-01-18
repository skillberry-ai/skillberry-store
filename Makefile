# Root Makefile for all Skillberry projects. 
# 0. Make sure you have git subtree and gh CLI installed
# 1. Copy this file from skillberry-common/default/Makefile.default to your project root as Makefile
# 2. Create folder .mk in your project root
# 3. Create .mk/local.mk (copy from skillberry-common/default/local.mk.default). Set the mandatory defs.
# 4. Customize additional content if needed.

SB_COMMON_REPO := git@github.ibm.com:skillberry/skillberry-common.git
SB_COMMON_BRANCH := main
SB_COMMON_REMOTE := skillberry-common
SB_COMMON_PATH := skillberry-common

_ensure_git_remote := $(shell \
    git remote | grep -Fxq "$(SB_COMMON_REMOTE)" || { \
        echo "$(SB_COMMON_REMOTE) remote does not exist - adding it"; \
        git remote add "$(SB_COMMON_REMOTE)" "$(SB_COMMON_REPO)"; \
    })


include $(SB_COMMON_PATH)/Makefile
include .mk/local.mk

# If the Makefile of skillberry-common is not available, install skillberry-common folder with the contents of skillberry-common repo from branch main (defaults)
$(SB_COMMON_PATH)/Makefile: 
	@echo "Adding $(SB_COMMON_REMOTE) under relative path $(SB_COMMON_PATH)"
	@git subtree add --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) 

