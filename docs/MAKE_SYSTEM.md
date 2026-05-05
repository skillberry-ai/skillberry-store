# Make System Documentation

## Overview

The Skillberry Store project uses GNU Make for build automation, development workflows, and deployment. This document explains the simplified Make system structure and how to use it effectively.

## Quick Start

```bash
# Show all available targets with descriptions
make help

# Install dependencies
make install

# Run tests
make test

# Run the service locally
make run

# Stop the service
make stop

# Build Docker image
make docker-build

# Run in Docker
make docker-run
```

## File Structure

```
skillberry-store/
├── Makefile              # Main Makefile (simplified, self-contained)
├── .mk/
│   ├── local.mk         # Project-specific configuration
│   ├── dev.mk           # Development-specific targets
│   └── process.mk       # Service lifecycle targets
└── docs/
    └── MAKE_SYSTEM.md   # This file
```

## Core Concepts

### 1. Project Configuration (.mk/local.mk)

This file contains all project-specific settings:

```makefile
# Project identity
ASSET_NAME := skillberry-store
SERVICE_NAME := skillberry-store
SERVICE_ENTRY_MODULE := skillberry_store.main

# Service configuration
SERVICE_PORTS := 8000 8002
SERVICE_HOST := 0.0.0.0
```

**Key Variables:**
- `ASSET_NAME`: Project name (used for Docker images, etc.)
- `SERVICE_NAME`: Service name (used for process management)
- `SERVICE_ENTRY_MODULE`: Python module to run (e.g., `skillberry_store.main`)
- `SERVICE_PORTS`: Space-separated list of ports (first is main port)
- `SERVICE_HOST`: Host to bind to (usually `0.0.0.0` or `localhost`)

### 2. Version Management

The system automatically generates version strings based on git state:

- **Tagged release**: `0.5.3`
- **After release**: `0.5.3-5-gc9b7ddd` (5 commits after tag 0.5.3)
- **Uncommitted changes**: `0.5.3-5-gc9b7ddd-dirty`
- **No releases yet**: `gc9b7ddd` (just commit hash)

Version is automatically written to `src/skillberry_store/fast_api/git_version.py`.

### 3. Virtual Environment

The system expects you to work in a Python virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
make install
```

## Common Targets

### Development

| Target | Description |
|--------|-------------|
| `make help` | Show all available targets with descriptions |
| `make install` | Install project dependencies |
| `make install ODEPS=dev` | Install with optional dependencies (e.g., dev, test) |
| `make test` | Run unit tests |
| `make test-e2e` | Run end-to-end tests |
| `make lint` | Check code formatting |

### Service Management

| Target | Description |
|--------|-------------|
| `make run` | Start the service locally |
| `make stop` | Stop the running service |
| `make clean` | Stop service and clean temporary files |
| `make clean-service-data` | Clean service-specific data |

### Docker Operations

| Target | Description |
|--------|-------------|
| `make docker-build` | Build Docker image locally |
| `make docker-run` | Run service in Docker container |
| `make docker-stop` | Stop Docker container |
| `make docker-clean` | Stop and remove Docker container |
| `make docker-rmi` | Remove Docker image and container |

### Release Management

| Target | Description |
|--------|-------------|
| `make release RELEASE_VERSION=1.0.0` | Create a new release |
| `make update-sdk` | Update SDK after API changes |

## Environment Variables

### Service Ports

The system automatically generates port environment variables:

```bash
# For SERVICE_PORTS := 8000 8002
# And SERVICE_PORT_ROLES := MAIN UI
# Generates:
SBS_MAIN_PORT=8000
SBS_UI_PORT=8002
SBS_HOST=0.0.0.0
```

These are stored in `.stamps/srv.env` and sourced when running the service.

### LLM Services (Optional)

If your service uses LLM services, set `USE_LLM_SVCS := 1` in `.mk/local.mk` and provide:

```bash
export RITS_API_KEY=your_key
# OR
export WATSONX_APIKEY=your_key
export WATSONX_PROJECT_ID=your_project
export WATSONX_URL=your_url
```

## Docker Configuration

### Image Naming

Images follow this pattern:
```
ghcr.io/skillberry-ai/skillberry-store:0.5.3
ghcr.io/skillberry-ai/skillberry-store:latest
```

### Multi-Architecture Support

To build and push multi-architecture images:

```bash
# Build for local architecture only (default)
make docker-build

# Build and push for multiple architectures (requires buildx)
make docker-build DBT=registry
```

Supported architectures: `linux/amd64`, `linux/arm64`

### Development Mode

To always build locally instead of pulling from registry:

```bash
export SBD_DEV=1
make docker-run  # Will build instead of pull
```

## Release Process

Creating a new release:

```bash
# 1. Ensure you're on main branch with clean working directory
git checkout main
git pull

# 2. Create release (creates tag, branch, and GitHub release)
make release RELEASE_VERSION=1.0.0

# This will:
# - Create branch-1.0.0
# - Tag as 1.0.0
# - Push tag to GitHub
# - Create GitHub release with notes
# - Build and push Docker image
```

## Troubleshooting

### "Not in virtual environment" Error

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate
```

### "Service already running" Error

```bash
# Stop the existing service
make stop

# Or check the PID file
cat /tmp/skillberry-store-service.pid
```

### Docker Build Fails

```bash
# Clean everything and rebuild
make docker-rmi
make docker-build
```

### Port Already in Use

```bash
# Check what's using the port
lsof -i :8000

# Stop the service
make stop

# Or change ports in .mk/local.mk
```

## Advanced Usage

### Custom Optional Dependencies

```bash
# Install with multiple optional dependency groups
make install ODEPS=dev,test,docs
```

### Custom Docker Registry

```bash
# Override registry in .mk/local.mk or environment
export REGISTRY_HOST=my-registry.com
export DOCKER_PROJECT=my-project
make docker-build
```

### Running Specific Tests

```bash
# Run specific test file
pytest src/skillberry_store/tests/test_specific.py

# Run with coverage
pytest --cov=skillberry_store
```

## Best Practices

1. **Always work in a virtual environment**
2. **Run `make install` after pulling changes**
3. **Use `make help` to discover available targets**
4. **Check `make lint` before committing**
5. **Run `make test` before pushing**
6. **Use descriptive commit messages**
7. **Keep `.mk/local.mk` updated with project changes**

## Getting Help

- Run `make help` to see all available targets
- Check this documentation for detailed explanations
- Review inline comments in Makefile and .mk files
- Ask team members or check project README

## Glossary

- **Target**: A Make command (e.g., `make install`)
- **Dependency**: A target that must run before another target
- **Stamp file**: A file in `.stamps/` that tracks when a target last ran
- **ODEPS**: Optional dependencies parameter for `make install`
- **DBT**: Docker Build Target (local or registry)
- **SBD_DEV**: Skillberry Development mode flag
