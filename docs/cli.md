# Skillberry Store CLI Documentation

The Skillberry Store SDK includes an auto-generated command-line interface (CLI) that provides convenient access to all API operations from your terminal.

## Overview

The CLI is built as a wrapper around [restish](https://rest.sh/), a powerful REST API client that automatically generates commands from OpenAPI specifications. This means:

- **Auto-generated commands** for all API endpoints
- **Type-safe parameters** based on the OpenAPI schema
- **Automatic documentation** from API descriptions
- **Multiple output formats** (JSON, YAML, table)

## Installation

The CLI is included with the Python SDK:

```bash
pip install skillberry-store-sdk
```

### Prerequisites

The CLI requires `restish` to be installed. If not present, the CLI will provide installation instructions:

**Option 1: Using Go**
```bash
go install github.com/rest-sh/restish@latest
```

**Option 2: Download pre-built binaries**
- Visit [restish releases](https://github.com/rest-sh/restish/releases)
- Download the appropriate binary for your platform
- Add it to your PATH

## Basic Usage

The CLI command is `sbs` (Skillberry Store):

```bash
sbs --help                    # Show all available commands
sbs <command> [args] [flags]  # General command structure
```

## Configuration

### Default Connection

By default, the CLI connects to `http://0.0.0.0:8000`. The configuration is automatically created in `~/.config/restish/apis.json` on first use.

### Connecting to Different Servers

To connect to a different server:

```bash
sbs connect http://production-server:8000
sbs connect https://staging.example.com
```

The CLI will remember this connection for future commands.

## Command Reference

### Skills Management

```bash
# List all skills
sbs list-skills

# Get a specific skill
sbs get-skill <skill-name>

# Create a new skill
sbs create-skill --name my-skill --description "My skill"

# Update a skill
sbs update-skill <skill-name> --description "Updated description"

# Delete a skill
sbs delete-skill <skill-name>

# Search skills semantically
sbs search-skills --search-term "data processing"

# Anthropic skill import/export
sbs detect-anthropic-skills
sbs import-anthropic-skill
sbs export-anthropic-skill <skill-name>
```

### Tools Management

```bash
# List all tools
sbs list-tools

# Get a specific tool
sbs get-tool <tool-name>

# Get the source module of a tool
sbs get-tool-module <tool-name>

# Search tools semantically
sbs search-tools --search-term "calculator functions"

# Execute a tool
sbs execute-tool <tool-name> --body='{"params":{"x":5,"y":3}}'

# Add a tool from a Python file
sbs add-tool

# Update or delete a tool
sbs update-tool <tool-name>
sbs delete-tool <tool-name>
```

### Snippets Management

```bash
# List all snippets
sbs list-snippets

# Get a specific snippet
sbs get-snippet <snippet-name>

# Create a snippet
sbs create-snippet --name helper --description "Helper utilities"

# Update or delete a snippet
sbs update-snippet <snippet-name>
sbs delete-snippet <snippet-name>

# Search snippets semantically
sbs search-snippets --search-term "string utilities"
```

### VMCP Servers

```bash
# List virtual MCP servers
sbs list-vmcp-servers

# Get a specific VMCP server
sbs get-vmcp-server <server-name>

# Create a VMCP server
sbs create-vmcp-server --name my-server --skill-uuid <uuid>

# Start, update, or delete a VMCP server
sbs start-vmcp-server <server-name>
sbs update-vmcp-server <server-name>
sbs delete-vmcp-server <server-name>

# Search VMCP servers
sbs search-vmcp-servers --search-term "math tools"
```

### vNFS Servers

```bash
# List virtual NFS servers
sbs list-vnfs-servers

# Get a specific vNFS server
sbs get-vnfs-server <server-name>

# Create a vNFS server
sbs create-vnfs-server --name my-server --skill-uuid <uuid>

# Start, update, or delete a vNFS server
sbs start-vnfs-server <server-name>
sbs update-vnfs-server <server-name>
sbs delete-vnfs-server <server-name>

# Search vNFS servers
sbs search-vnfs-servers --search-term "data files"
```

### Admin

```bash
# Health checks
sbs health
sbs health-ready

# Prometheus metrics
sbs metrics

# Delete all data (irreversible)
sbs purge-all
```

## Advanced Features

### Output Formats

Restish supports multiple output formats:

```bash
# JSON output (default)
sbs list-tools

# YAML output
sbs list-tools -o yaml

# Table output
sbs list-tools -o table

# Raw output
sbs list-tools -o raw
```

### Filtering and Pagination

```bash
# Filter results
sbs list-tools --filter='state=active'

# Limit results
sbs list-tools --limit=10

# Pagination
sbs list-tools --offset=20 --limit=10
```

### Request Body from File

For complex requests, use a file:

```bash
# Create tool from JSON file
sbs create-tool --body=@tool-definition.json

# Update skill from YAML file
sbs update-skill <skill-name> --body=@skill-update.yaml
```

### Verbose Mode

See detailed request/response information:

```bash
sbs list-tools -v
```

## Architecture

The CLI works through the following flow:

1. **Auto-configuration**: On first run, the CLI:
   - Creates `~/.config/restish/apis.json`
   - Registers the API with the OpenAPI spec URL
   - Syncs the spec to generate commands

2. **Command delegation**: All commands are passed to `restish`:
   ```
   sbs list-tools → restish sbs list-tools
   ```

3. **Output filtering**: The CLI filters restish output to:
   - Remove generic "Global Flags" section
   - Add custom help text
   - Show current connection URL

## Troubleshooting

### CLI not found after installation

Ensure the Python scripts directory is in your PATH:

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows
# Add %APPDATA%\Python\Scripts to your PATH
```

### Restish not installed

Follow the installation instructions provided by the CLI or visit [restish documentation](https://rest.sh/).

### Connection refused

Ensure the Skillberry Store service is running:

```bash
# Check if service is running
curl http://localhost:8000/docs

# Start the service
make run
```

### API spec sync failed

Manually sync the API spec by clearing the cache and re-running any command:

```bash
rm ~/.cache/restish/sbs.cbor
sbs --help
```

## Examples

### Complete Workflow Example

```bash
# 1. Connect to your server
sbs connect http://localhost:8000

# 2. List existing tools
sbs list-tools

# 3. Add a new tool
sbs create-tool --name calculator --description "Basic calculator"

# 4. Execute the tool
sbs execute-tool calculator --body='{"params":{"x":5,"y":3}}'

# 5. Create a skill using the tool
sbs create-skill --name math-skill --description "Math utilities"

# 6. List skills to verify
sbs list-skills
```

### Batch Operations

```bash
# Export all tools
sbs list-tools -o json > tools-backup.json

# Import tools from backup
cat tools-backup.json | jq -c '.[]' | while read tool; do
  sbs create-tool --body="$tool"
done
```

## Integration with Scripts

The CLI can be easily integrated into shell scripts:

```bash
#!/bin/bash

# Check if tool exists
if sbs get-tool my-tool 2>/dev/null; then
  echo "Tool exists"
else
  echo "Creating tool..."
  sbs create-tool --body=@tool.json
fi

# Get tool output as JSON
RESULT=$(sbs execute-tool my-tool --body='{"params":{}}' -o json)
echo "Result: $RESULT"
```

## Related Documentation

- [Skillberry Store API Documentation](http://localhost:8000/docs)
- [Restish Documentation](https://rest.sh/)
- [Python SDK Documentation](https://github.com/skillberry-ai/skillberry-store-sdk)
- [Configuration Guide](config-env-vars.md)

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review [API documentation](http://localhost:8000/docs)
- Contact the development team
