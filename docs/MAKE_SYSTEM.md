# Skillberry Store Make System Documentation

## Overview

The Skillberry Store uses GNU Make as its build and automation system. This document explains the structure, targets, and usage patterns to help maintainers understand and modify the system.

## Quick Start

```bash
# Show all available targets with descriptions
make help

# Install dependencies
make install-requirements

# Run the service locally
make run

# Run tests
make test

# Build and run with Docker
make docker-run

# Stop the service
make stop
```

## File Structure

The Make system is organized into several files:

```
skillberry-store/
├── Makefile                    # Root Makefile (subtree management)
├── .mk/
│   ├── local.mk               # Project configuration (REQUIRED)
│   ├── dev.mk                 # Project-specific development targets
│   └── process.mk             # Project-specific process targets
└── skillberry-common/         # Shared Make system (git subtree)
    ├── Makefile               # Includes all common .mk files
    └── .mk/
        ├── globals.mk         # Global variables and utilities
        ├── dev.mk             # Development targets
        ├── process.mk         # Process management targets
        ├── docker.mk          # Docker/Podman operations
        ├── ci.mk              # CI/CD targets
        └── common.mk          # Subtree operations
```

## Configuration

### Required Configuration (.mk/local.mk)

This file contains project-specific settings that **must** be configured:

```makefile
# Project identifiers
ASSET_NAME := skillberry-store          # Project name (no spaces, lowercase)
ACRONYM := SBS                          # Short acronym (uppercase)
DESC_NAME := Skillberry Store service   # Human-readable description

# Version tracking
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py

# LLM services (0 or 1)
USE_LLM_SVCS := 0                      # Set to 1 if using Watson/RITS

# Service configuration
SERVICE_ENTRY_MODULE := skillberry_store.main  # Python module to run
SERVICE_NAME := $(ASSET_NAME)
SERVICE_PORTS := 8000 8002             # Main port, UI port
SERVICE_PORT_ROLES := MAIN UI          # Port role names
SERVICE_HOST := 0.0.0.0                # Bind address
SERVICE_HAS_SDK := 1                   # Set to 1 if SDK is generated
```

### Environment Variables

Key environment variables that affect behavior:

- **SBS_BASE_DIR**: Base directory for data storage (default: system temp)
- **SBS_PORT**: Override main service port (default: 8000)
- **SBS_HOST**: Override service host (default: 0.0.0.0)
- **ENABLE_UI**: Enable/disable web UI (default: true)
- **OBSERVABILITY**: Enable/disable metrics/traces (default: true)
- **ODEPS**: Optional dependencies to install (e.g., `dev`, `vllm`)
- **DBT**: Docker Build Target - `local` or `registry` (default: local)
- **SBD_DEV**: Skip Docker pull, always build locally (default: unset)
- **RELEASE_VERSION**: Version for release target (e.g., `1.2.3`)

## Common Targets

### Development Targets

#### `make help`
Display all available targets with descriptions. This is the default target.

#### `make install-requirements`
Install Python dependencies. Automatically:
- Verifies you're in a virtual environment
- Checks Python version compatibility
- Installs/updates pip and uv
- Installs project dependencies
- Sets up git hooks

Optional dependencies:
```bash
make install-requirements ODEPS=dev        # Install dev dependencies
make install-requirements ODEPS=dev,vllm   # Install multiple groups
```

#### `make test`
Run unit tests using pytest.

#### `make test-e2e`
Run end-to-end tests.

#### `make lint`
Check code formatting with black. Fails if formatting issues are found.

### Process Management Targets

#### `make run`
Start the service as a local process. Creates:
- `/tmp/skillberry-store-service.pid` - Process ID file
- `/tmp/skillberry-store.log` - Service log file

The service runs in the background and can be stopped with `make stop`.

#### `make stop`
Stop the running service gracefully.

#### `make clean`
Stop the service and clean up:
- PID and log files
- Python cache directories
- Build artifacts

#### `make clean-service-data`
Clean service-specific data (defined per project).

### Docker Targets

#### `make docker-run`
Run the service in a Docker container. Automatically:
1. Tries to pull the latest image from GitHub Container Registry
2. Falls back to building locally if pull fails
3. Starts the container with proper port mappings

To force local build:
```bash
SBD_DEV=1 make docker-run
```

#### `make docker-build`
Build the Docker image locally for your architecture.

To build and push multi-architecture images:
```bash
DBT=registry make docker-build
```

#### `make docker-stop`
Stop the running Docker container.

#### `make docker-clean`
Stop and remove the Docker container (keeps the image).

#### `make docker-rmi`
Remove the Docker container and image.

#### `make docker-pull`
Pull the latest image from the registry.

### Release Targets

#### `make release`
Create a new release. This target:
1. Verifies you're on the main branch
2. Checks for uncommitted changes
3. Creates a release branch (`branch-X.Y.Z`)
4. Creates a git tag
5. Pushes the tag to GitHub
6. Creates a GitHub release with notes
7. Builds and pushes Docker images

Usage:
```bash
RELEASE_VERSION=1.2.3 make release
```

#### `make update-sdk`
Generate and update the Python SDK from the OpenAPI spec. Only runs if `SERVICE_HAS_SDK=1`.

### CI/CD Targets

#### `make ci-pull-request`
Run all checks for pull requests:
- Linting
- Unit tests
- End-to-end tests

#### `make ci-push`
Run all checks for pushes to main:
- All PR checks
- Docker build and push
- SDK update

### Subtree Management Targets

These targets manage the `skillberry-common` subtree:

#### `make fetch-common`
Fetch updates from the skillberry-common repository.

#### `make status-common`
Show local commits in skillberry-common that haven't been pushed upstream.

#### `make pull-common`
Pull updates from skillberry-common into your project.

#### `make push-common`
Push local skillberry-common changes upstream (not recommended - use split-common instead).

#### `make split-common`
Create a PR branch for contributing changes back to skillberry-common.

## Version Management

The system automatically generates version strings based on git history:

- **On a release tag**: `1.2.3`
- **After a release**: `1.2.3-5-gc9b7ddd` (5 commits after 1.2.3)
- **With uncommitted changes**: `1.2.3-5-gc9b7ddd-dirty`
- **No releases yet**: `gc9b7ddd` (just the commit hash)

The version is:
1. Calculated in `globals.mk` as `BUILD_VERSION`
2. Written to `VERSION_LOCATION` file
3. Embedded in Docker images
4. Used for image tagging

## Docker/Podman Support

The system supports both Docker and Podman:

1. **Auto-detection**: Checks shell config files for `alias docker='podman'`
2. **Multi-architecture**: Supports building for `linux/amd64` and `linux/arm64`
3. **Registry operations**: Can push to GitHub Container Registry

### Docker Build Targets

- **DBT=local** (default): Build for your architecture only
- **DBT=registry**: Build for all architectures and push to registry

### Base Image

The system uses a base image (`skillberry-base`) that contains common dependencies:

```bash
make base-image-build              # Build locally
DBT=registry make base-image-build # Build and push multi-arch
make base-image-rm                 # Remove local base image
```

## Python Version Support

Supported Python versions are defined in `dev.mk`:

```makefile
SUPPORTED_PYTHON_VERSIONS := 3.11 3.12.10
```

The system checks your Python version during `install-requirements` and fails if incompatible.

## Troubleshooting

### "Not in virtual environment" error
Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### Docker pull fails
The system will automatically fall back to building locally. To force local builds:
```bash
export SBD_DEV=1
make docker-run
```

### Multi-arch build fails
Ensure Docker buildx is set up:
```bash
docker buildx create --use
docker buildx inspect --bootstrap
```

### Service won't start
Check the log file:
```bash
tail -f /tmp/skillberry-store.log
```

### Port already in use
Change the port:
```bash
SBS_PORT=8001 make run
```

## Best Practices

1. **Always use virtual environments** - The system enforces this
2. **Run tests before committing** - Use `make test` and `make lint`
3. **Use semantic versioning** - Follow X.Y.Z format for releases
4. **Document new targets** - Add `## Description` comments
5. **Keep .mk/local.mk updated** - Ensure configuration is accurate
6. **Test Docker builds** - Run `make docker-run` before releasing
7. **Review changes** - Use `make status-common` before updating subtree

## Adding New Targets

To add a new Make target:

1. Choose the appropriate .mk file:
   - Project-specific: `.mk/dev.mk` or `.mk/process.mk`
   - Shared across projects: `skillberry-common/.mk/*.mk`

2. Add the target with documentation:
```makefile
##@ Category Name

my-target: dependencies ## Description of what this target does
	@echo "Running my target"
	# Commands here
```

3. Test the target:
```bash
make my-target
make help  # Verify it appears in help
```

## Advanced Topics

### Stamp Files

The system uses `.stamps/` directory for tracking state:
- `.stamps/install-requirements-*`: Tracks installed dependencies
- `.stamps/docker-build-*`: Tracks Docker builds
- `.stamps/code-scan`: Tracks code changes
- `.stamps/srv.env`: Generated service environment variables

### SSH Agent for Git Dependencies

For private git dependencies during Docker builds:
```bash
make ssh-agent  # Start/capture SSH agent
```

### Custom Service Data Cleanup

Override `clean-service-data` in `.mk/process.mk`:
```makefile
clean-service-data: stop
	@echo "Cleaning custom data"
	rm -rf /tmp/my-custom-data
```

## Getting Help

- Run `make help` for available targets
- Check this documentation for detailed explanations
- Review the .mk files for implementation details
- Ask the team for clarification on complex targets
