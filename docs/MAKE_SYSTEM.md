# Make System Documentation

## Overview

The Skillberry Store uses a modular Make-based build system to manage development, testing, deployment, and release workflows. This document explains the structure, common tasks, and how to customize the system.

## Quick Start

### Common Commands

```bash
# Development
make help                    # Show all available commands
make install-requirements    # Install Python dependencies
make test                    # Run tests
make lint                    # Check code formatting
make run                     # Run the service locally
make stop                    # Stop the running service

# Docker
make docker-build           # Build Docker image locally
make docker-run             # Run service in Docker container
make docker-stop            # Stop Docker container
make docker-clean           # Remove Docker container

# Release (maintainers only)
make release RELEASE_VERSION=1.0.0  # Create a new release
```

## System Architecture

### File Structure

```
skillberry-store/
├── Makefile                 # Root Makefile (includes common system)
├── .mk/                     # Project-specific Make files
│   ├── local.mk            # Project configuration (REQUIRED)
│   ├── dev.mk              # Development-specific targets
│   └── process.mk          # Service lifecycle management
└── skillberry-common/       # Shared Make system (git subtree)
    ├── Makefile            # Common system entry point
    └── .mk/                # Shared Make modules
        ├── globals.mk      # Global variables and utilities
        ├── dev.mk          # Common development targets
        ├── process.mk      # Service management targets
        ├── docker.mk       # Docker build/run targets
        ├── ci.mk           # CI/CD targets
        └── common.mk       # Shared utilities
```

### How It Works

1. **Root Makefile**: Entry point that includes `skillberry-common` subtree
2. **local.mk**: Project-specific configuration (service name, ports, etc.)
3. **Modular .mk files**: Organized by functionality (dev, docker, CI, etc.)
4. **Inheritance**: Project .mk files can override common targets

## Configuration

### Required: .mk/local.mk

This file contains project-specific settings:

```makefile
# Service Identity
ASSET_NAME := skillberry-store          # Project name (no spaces, use hyphens)
ACRONYM := SBS                          # Short acronym for CLI tools
DESC_NAME := Skillberry Store service   # Human-readable description

# Version Management
VERSION_LOCATION := src/skillberry_store/fast_api/git_version.py

# Service Configuration
SERVICE_ENTRY_MODULE := skillberry_store.main  # Python module to run
SERVICE_NAME := $(ASSET_NAME)                  # Service name (usually same as ASSET_NAME)
SERVICE_PORTS := 8000 8002                     # Space-separated list of ports
SERVICE_PORT_ROLES := MAIN UI                  # Role names for each port
SERVICE_HOST := 0.0.0.0                        # Host to bind to

# Features
USE_LLM_SVCS := 0        # Set to 1 if using LLM services (requires API keys)
SERVICE_HAS_SDK := 1     # Set to 1 if service generates an SDK
```

### Optional: Custom Targets

Add project-specific targets in `.mk/dev.mk` or `.mk/process.mk`:

```makefile
# .mk/dev.mk
test-e2e: ## Run end-to-end tests
	pytest src/skillberry_store/tests/e2e

lint: ## Check code formatting
	black --check src/
```

## Key Concepts

### 1. Stamp Files (.stamps/)

The system uses "stamp files" to track completed operations and avoid redundant work:

- `.stamps/install-requirements-*`: Tracks installed dependencies
- `.stamps/docker-build-*`: Tracks built Docker images
- `.stamps/code-scan`: Tracks code changes
- `.stamps/srv.env`: Generated service environment variables

**Why?** Make uses file timestamps to determine if targets need rebuilding. Stamp files provide this mechanism for operations that don't produce a single output file.

### 2. Build Version

The system automatically generates a version string based on Git state:

- `0.5.3` - On a release tag
- `0.5.3-5-gc9b7ddd` - 5 commits after tag 0.5.3
- `0.5.3-5-gc9b7ddd-dirty` - Same, but with uncommitted changes
- `gc9b7ddd` - No releases yet, just commit hash

This version is:
- Written to `VERSION_LOCATION` file
- Embedded in Docker images
- Used for tagging releases

### 3. Service Ports

Services can expose multiple ports with specific roles:

```makefile
SERVICE_PORTS := 8000 8002
SERVICE_PORT_ROLES := MAIN UI
```

This generates environment variables:
- `SBS_MAIN_PORT=8000`
- `SBS_UI_PORT=8002`
- `SBS_HOST=0.0.0.0`

### 4. Docker Build Targets (DBT)

The system supports two Docker build modes:

```bash
# Local build (single architecture)
make docker-build                    # Builds for your machine's architecture
make docker-build DBT=local          # Same as above (explicit)

# Registry build (multi-architecture)
make docker-build DBT=registry       # Builds for linux/amd64 and linux/arm64
                                     # Pushes to GitHub Container Registry
```

**Requirements for multi-arch builds:**
- Docker Buildx with multi-platform support
- Authenticated to GitHub Container Registry

### 5. Development Mode (SBD_DEV)

Controls whether `make docker-run` pulls or builds images:

```bash
# Default: Try to pull from registry, build if pull fails
make docker-run

# Development mode: Always build locally
SBD_DEV=1 make docker-run
export SBD_DEV=1              # Set for entire session
```

## Common Workflows

### Setting Up Development Environment

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
make install-requirements

# 3. Run tests to verify setup
make test
```

### Running the Service Locally

```bash
# Start service
make run

# In another terminal, test it
curl http://localhost:8000/health

# Stop service
make stop

# Clean up all runtime data
make clean
```

### Working with Docker

```bash
# Build and run in Docker
make docker-build
make docker-run

# View logs
docker logs skillberry-store

# Stop and clean up
make docker-stop
make docker-clean

# Remove image completely
make docker-rmi
```

### Making Code Changes

```bash
# 1. Make your changes
vim src/skillberry_store/main.py

# 2. Check formatting
make lint

# 3. Run tests
make test

# 4. If tests pass, commit
git add .
git commit -m "Your change description"
```

### Creating a Release (Maintainers)

```bash
# 1. Ensure you're on main branch with clean state
git checkout main
git pull

# 2. Create release (this will build and push Docker image)
make release RELEASE_VERSION=1.0.0

# This will:
# - Create branch-1.0.0 branch
# - Tag as 1.0.0
# - Push tag to GitHub
# - Create GitHub release with notes
# - Build and push Docker image
# - Update SDK if SERVICE_HAS_SDK=1
```

## Troubleshooting

### "Unimplemented target" Error

**Problem:** `make: *** [Makefile:XX: some-target] Error 1`

**Solution:** The target doesn't exist. Check available targets with `make help`.

### Virtual Environment Issues

**Problem:** `❌ Not in virtual environment`

**Solution:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### Docker Build Fails

**Problem:** Multi-arch build fails with "multiple platforms feature is currently not supported"

**Solution:** You need Docker Buildx:
```bash
docker buildx create --use
docker buildx inspect --bootstrap
```

### Port Already in Use

**Problem:** Service fails to start: "Address already in use"

**Solution:**
```bash
# Find process using the port
lsof -i :8000  # On Linux/Mac
netstat -ano | findstr :8000  # On Windows

# Stop the service properly
make stop

# Or kill the process
kill -9 <PID>
```

### Missing Environment Variables

**Problem:** Service fails with "WATSONX_APIKEY is not set"

**Solution:** If `USE_LLM_SVCS=1`, you need to set LLM service credentials:
```bash
export WATSONX_APIKEY="your-key"
export WATSONX_PROJECT_ID="your-project"
export WATSONX_URL="https://api.watsonx.ai"
```

Or use RITS:
```bash
export RITS_API_KEY="your-key"
```

## Advanced Topics

### Customizing the Build

#### Adding Optional Dependencies

Edit `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = ["pytest", "black"]
gpu = ["torch", "cuda-toolkit"]
```

Install with:
```bash
make install-requirements ODEPS=dev,gpu
```

#### Custom Docker Volumes

Edit `.mk/local.mk`:
```makefile
CNTR_MOUNTS := /host/path:/container/path /another/path:/mount
```

### Extending the System

#### Adding New Make Targets

Create targets in `.mk/dev.mk`:
```makefile
##@ Custom Tasks

my-task: install-requirements  ## Description of my task
	@echo "Running my custom task"
	python scripts/my_script.py
```

The `##@` creates a new section in `make help`, and `##` adds the description.

#### Overriding Common Targets

You can override targets from `skillberry-common` by redefining them in your local `.mk` files. The last definition wins.

### Understanding the Subtree

The `skillberry-common` directory is a Git subtree - a copy of another repository embedded in this one. This allows sharing common Make logic across multiple projects.

**Updating the subtree:**
```bash
# Pull latest changes from skillberry-common
git subtree pull --prefix skillberry-common skillberry-common main --squash
```

**Note:** Most developers don't need to update the subtree. This is typically done by maintainers.

## Glossary

- **ASSET_NAME**: The project's identifier (e.g., `skillberry-store`)
- **ACRONYM**: Short form used for CLI tools and environment variables (e.g., `SBS`)
- **BUILD_VERSION**: Auto-generated version string from Git state
- **DBT (Docker Build Target)**: Build mode - `local` or `registry`
- **ODEPS (Optional Dependencies)**: Extra dependency groups to install
- **SBD_DEV**: Development mode flag for Docker operations
- **SERVICE_ENTRY_MODULE**: Python module path to run the service
- **Stamp file**: Marker file tracking completed operations
- **Subtree**: Git mechanism for embedding one repository in another

## Getting Help

1. **List all commands**: `make help`
2. **Check this documentation**: `docs/MAKE_SYSTEM.md`
3. **View Make file**: Look at `Makefile` and `.mk/*.mk` files
4. **Ask the team**: Create an issue or ask in team chat

## Best Practices

1. **Always use virtual environment**: Prevents dependency conflicts
2. **Run tests before committing**: `make test`
3. **Check formatting**: `make lint` before pushing
4. **Use stamp files**: Don't delete `.stamps/` directory manually
5. **Document custom targets**: Add `##` comments for `make help`
6. **Keep local.mk updated**: When adding new services or changing ports
7. **Use SBD_DEV for development**: Faster iteration when building Docker images

## Migration from Old System

If you're updating from an older version of the Make system:

1. **Backup your local.mk**: `cp .mk/local.mk .mk/local.mk.backup`
2. **Update subtree**: `git subtree pull --prefix skillberry-common skillberry-common main --squash`
3. **Review changes**: Compare your backup with new template
4. **Test thoroughly**: Run `make test` and `make docker-build`
5. **Update CI/CD**: Ensure GitHub Actions still work

## Contributing

When modifying the Make system:

1. **Test changes**: Verify all common workflows still work
2. **Update documentation**: Keep this file in sync with changes
3. **Add examples**: Show how to use new features
4. **Consider compatibility**: Don't break existing projects
5. **Document breaking changes**: Clearly mark in commit messages
