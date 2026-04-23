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
sbs <resource> <action>       # General command structure
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

## Common Commands

### Skills Management

```bash
# List all skills
sbs list-skills-skills-get list

# Get a specific skill
sbs get-skill-skills-name-get <skill-name>

# Create a new skill
sbs create-skill-skills-post --body='{"name":"my-skill","description":"My skill"}'

# Delete a skill
sbs delete-skill-skills-name-delete <skill-name>
```

### Tools Management

```bash
# List all tools
sbs list-tools-tools-get list

# Get a specific tool
sbs get-tool-tools-name-get <tool-name>

# Search tools semantically
sbs search-tools-tools-search-get --query="calculator functions"

# Execute a tool
sbs execute-tool-tools-name-execute-post <tool-name> --body='{"params":{"x":5,"y":3}}'
```

### Snippets Management

```bash
# List all snippets
sbs list-snippets-snippets-get list

# Get a specific snippet
sbs get-snippet-snippets-name-get <snippet-name>

# Create a snippet
sbs create-snippet-snippets-post --body='{"name":"helper","code":"def helper(): pass"}'
```

### VMCP Servers

```bash
# List virtual MCP servers
sbs list-vmcp-servers-vmcp-servers-get list

# Get a specific VMCP server
sbs get-vmcp-server-vmcp-servers-name-get <server-name>

# Create a VMCP server
sbs create-vmcp-server-vmcp-servers-post --body='{"name":"my-server","tools":["tool1","tool2"]}'
```

## Advanced Features

### Output Formats

Restish supports multiple output formats:

```bash
# JSON output (default)
sbs list-tools-tools-get list

# YAML output
sbs list-tools-tools-get list -o yaml

# Table output
sbs list-tools-tools-get list -o table

# Raw output
sbs list-tools-tools-get list -o raw
```

### Filtering and Pagination

```bash
# Filter results
sbs list-tools-tools-get list --filter='state=active'

# Limit results
sbs list-tools-tools-get list --limit=10

# Pagination
sbs list-tools-tools-get list --offset=20 --limit=10
```

### Request Body from File

For complex requests, use a file:

```bash
# Create tool from JSON file
sbs create-tool-tools-post --body=@tool-definition.json

# Update skill from YAML file
sbs update-skill-skills-name-put <skill-name> --body=@skill-update.yaml
```

### Verbose Mode

See detailed request/response information:

```bash
sbs list-tools-tools-get list -v
```

## Architecture

The CLI works through the following flow:

1. **Auto-configuration**: On first run, the CLI:
   - Creates `~/.config/restish/apis.json`
   - Registers the API with the OpenAPI spec URL
   - Syncs the spec to generate commands

2. **Command delegation**: All commands are passed to `restish`:
   ```
   sbs list-tools-tools-get list → restish sbs list-tools-tools-get list
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

Manually sync the API spec:

```bash
restish api sync sbs
```

## Examples

### Complete Workflow Example

```bash
# 1. Connect to your server
sbs connect http://localhost:8000

# 2. List existing tools
sbs list-tools-tools-get list

# 3. Add a new tool
sbs create-tool-tools-post --body='{
  "name": "calculator",
  "description": "Basic calculator",
  "code": "def add(x, y): return x + y"
}'

# 4. Execute the tool
sbs execute-tool-tools-name-execute-post calculator --body='{"params":{"x":5,"y":3}}'

# 5. Create a skill using the tool
sbs create-skill-skills-post --body='{
  "name": "math-skill",
  "tools": ["calculator"]
}'

# 6. List skills to verify
sbs list-skills-skills-get list
```

### Batch Operations

```bash
# Export all tools
sbs list-tools-tools-get list -o json > tools-backup.json

# Import tools from backup
cat tools-backup.json | jq -c '.[]' | while read tool; do
  sbs create-tool-tools-post --body="$tool"
done
```

## Integration with Scripts

The CLI can be easily integrated into shell scripts:

```bash
#!/bin/bash

# Check if tool exists
if sbs get-tool-tools-name-get my-tool 2>/dev/null; then
  echo "Tool exists"
else
  echo "Creating tool..."
  sbs create-tool-tools-post --body=@tool.json
fi

# Get tool output as JSON
RESULT=$(sbs execute-tool-tools-name-execute-post my-tool --body='{"params":{}}' -o json)
echo "Result: $RESULT"
```

## Related Documentation

- [Skillberry Store API Documentation](http://localhost:8000/docs)
- [Restish Documentation](https://rest.sh/)
- [Python SDK Documentation](https://github.ibm.com/skillberry/skillberry-store-sdk)
- [Configuration Guide](config-env-vars.md)

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review [API documentation](http://localhost:8000/docs)
- Contact the development team