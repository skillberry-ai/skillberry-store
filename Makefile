# Common Makefile defs and targets, arranged by categories

$(info Reading file: $(lastword $(MAKEFILE_LIST)))
$(info SB_COMMON_PATH = $(SB_COMMON_PATH))

include skillberry-common/.mk/globals.mk
include skillberry-common/.mk/dev.mk
include skillberry-common/.mk/process.mk
include skillberry-common/.mk/docker.mk
include skillberry-common/.mk/ci.mk
