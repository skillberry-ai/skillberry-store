# Make System Simplification

## Overview

The make system has been simplified by consolidating project-specific make targets into a single `.mk/local.mk` file, reducing complexity and improving maintainability.

## Changes Made

### Before
The project had three separate `.mk` files:
- `.mk/local.mk` - Project configuration and includes
- `.mk/dev.mk` - Development targets (test-e2e, lint)
- `.mk/process.mk` - Process management targets (clean-service-data)

### After
All project-specific targets are now consolidated into `.mk/local.mk`:
- Project configuration (ASSET_NAME, SERVICE_PORTS, etc.)
- Development targets (test-e2e, lint)
- Process management targets (clean-service-data)

### Files Removed
- `.mk/dev.mk` - Merged into `.mk/local.mk`
- `.mk/process.mk` - Merged into `.mk/local.mk`

## Structure

The simplified structure maintains the same functionality while reducing file count:

```
.mk/
└── local.mk          # All project-specific configuration and targets

skillberry-common/
├── Makefile          # Main common makefile
└── .mk/
    ├── globals.mk    # Global variables and utilities
    ├── dev.mk        # Common development targets
    ├── process.mk    # Common process management targets
    ├── docker.mk     # Docker container management
    ├── ci.mk         # CI/CD targets
    └── common.mk     # Common repository operations
```

## Benefits

1. **Reduced Complexity**: Fewer files to manage and maintain
2. **Easier Navigation**: All project-specific targets in one place
3. **Clearer Separation**: Project-specific vs. common targets are more distinct
4. **Maintained Functionality**: All make targets continue to work as before

## Usage

All make commands work exactly as before:

```bash
# Show available targets
make help

# Run tests
make test
make test-e2e

# Lint code
make lint

# Run service
make run
make stop

# Docker operations
make docker-build
make docker-run
```

## Migration Guide

For other projects using the same make system structure:

1. Copy the contents of `.mk/dev.mk` and `.mk/process.mk` into `.mk/local.mk`
2. Remove the `include .mk/dev.mk` and `include .mk/process.mk` lines from `.mk/local.mk`
3. Delete `.mk/dev.mk` and `.mk/process.mk` files
4. Test that all make targets still work: `make help`, `make test`, etc.

## Notes

- The common make system in `skillberry-common/` remains unchanged
- This simplification only affects project-specific targets
- All functionality is preserved
