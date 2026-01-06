# Root Makefile for all Skillberry projects. 
# 0. Make sure you have git subtree and gh CLI installed
# 1. Copy this file from skillberry-common/Makefile.default to your project root as Makefile
# 2. Create folder .mk in your project root
# 3. Create .mk/local.mk (copy from skillberry-common/.mk/local.mk.default). Set the mandatory defs.
# 4. Customize additional content if needed.

SB_COMMON_REPO := git@github.ibm.com:skillberry-staging/skillberry-common.git
SB_COMMON_BRANCH := main
SB_COMMON_REMOTE := skillberry-common
SB_COMMON_PATH := skillberry-common

include $(SB_COMMON_PATH)/Makefile
include .mk/local.mk

# If the Makefile of skillberry-common is not available, install skillberry-common folder with the contents of skillberry-common repo from branch main (defaults)
$(SB_COMMON_PATH)/Makefile: 
	@echo "Setting remote for $(SB_COMMON_REMOTE)"
	@git remote add -f $(SB_COMMON_REMOTE) $(SB_COMMON_REPO) 2>/dev/null || true
	@echo "Adding $(SB_COMMON_REMOTE) under relative path $(SB_COMMON_PATH)"
	@git subtree add --prefix $(SB_COMMON_PATH) $(SB_COMMON_REMOTE) $(SB_COMMON_BRANCH) 

