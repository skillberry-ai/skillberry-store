##@ Setup & teardown as a process

# Add ui-build as a prerequisite of the common `run` target so the UI static
# bundle exists (and is current with respect to sources and ACL config) before
# UIManager spawns `vite preview`. The recipe lives in skillberry-common.
run: ui-build

clean-service-data: stop
	@echo "Clean $(SERVICE_NAME) /tmp directory"
	+rm -rf /tmp/manifest
	+rm -rf /tmp/descriptions
	+rm -rf /tmp/files

