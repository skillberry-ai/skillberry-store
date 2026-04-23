# Connecting MCP as a Backend

This guide explains how to connect external MCP (Model Context Protocol) servers as backends to Skillberry Store, allowing you to consume and route tools from multiple MCP servers.

## Overview

Skillberry Store supports two ways of working with MCP:

1. **MCP Frontend**: Expose your Skillberry Store tools as virtual MCP servers
2. **MCP Backend**: Connect to external MCP servers and consume their tools

This document focuses on using MCP as a backend.

## What is MCP Backend Support?

MCP backend support allows you to:
- Connect to external MCP servers
- Import tools from those servers into Skillberry Store
- Execute tools on remote MCP servers
- Route tool calls to the appropriate backend MCP server

## Adding Tools from MCP Servers

When adding a tool to Skillberry Store that should be executed on an external MCP server, you need to specify the `packaging_format` as `"mcp"` and provide the `mcp_url` in the tool manifest.

### Tool Manifest Example

```json
{
  "name": "my_mcp_tool",
  "description": "A tool that runs on an external MCP server",
  "packaging_format": "mcp",
  "mcp_url": "http://localhost:8080/sse",
  "params": {
    "properties": {
      "param1": {
        "type": "string",
        "description": "First parameter"
      },
      "param2": {
        "type": "integer",
        "description": "Second parameter"
      }
    },
    "required": ["param1"]
  }
}
```

### Key Fields

- **packaging_format**: Must be set to `"mcp"` to indicate this tool runs on an MCP server
- **mcp_url**: The SSE endpoint URL of the external MCP server (e.g., `http://localhost:8080/sse`)
- **params**: Define the tool's parameters following the standard schema

## Environment Variables

You can set a default MCP server URL using the environment variable:

```bash
export MCP_SERVER_URL="http://localhost:8080/sse"
```

If `mcp_url` is not specified in the tool manifest, this default URL will be used.

## How It Works

When you execute a tool with `packaging_format: "mcp"`:

1. Skillberry Store extracts the function name and parameters from the tool manifest
2. It connects to the specified MCP server via SSE (Server-Sent Events)
3. It lists available tools on the MCP server
4. It calls the matching tool with the provided parameters
5. It returns the result to the caller

## Example: Using MCP Backend with Agent Frameworks

See the [Agent Framework Integration example](../src/skillberry_store/contrib/examples/agent_framework/connect_langgraph_client.py) for a complete example of connecting Skillberry Store to agent frameworks like LangGraph.

## Timeouts and Error Handling

The MCP backend implementation includes several timeouts to ensure reliability:

- **Session initialization**: 10 seconds
- **Tool listing**: 10 seconds  
- **Tool execution**: 30 seconds
- **SSE connection**: 30 seconds

If any timeout is exceeded, you'll receive a clear error message indicating the issue.

## Troubleshooting

### Connection Timeout

If you see: `Timeout connecting to MCP server at <url>`

**Solutions:**
- Verify the MCP server is running and accessible
- Check the URL is correct (should end with `/sse`)
- Ensure there are no firewall or network issues
- Check the MCP server logs for errors

### Tool Not Found

If you see: `Tool '<name>' not found in MCP server`

**Solutions:**
- Verify the tool name matches exactly (case-sensitive)
- List available tools on the MCP server to confirm the tool exists
- Check the MCP server is properly exposing the tool

### Parameter Mismatch

If you see parameter-related errors:

**Solutions:**
- Ensure the `params` in your manifest match the MCP server's tool schema
- Check that required parameters are provided
- Verify parameter types match expectations

## Related Documentation

- [Agent Framework Integration](../src/skillberry_store/contrib/examples/agent_framework/agent_framework.md)
- [MCP Protocol Specification](https://github.com/modelcontextprotocol)
- [Virtual MCP Servers (Frontend)](../README.md#engage-with-the-service-via-mcp-)

## Additional Resources

For more information about the Model Context Protocol, visit:
- [MCP GitHub Repository](https://github.com/modelcontextprotocol)
- [MCP Documentation](https://modelcontextprotocol.io)