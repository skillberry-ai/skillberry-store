# MCP Server Experiment Guide

## Steps to Experiment with the MCP Server

Follow these steps to set up and experiment with the MCP server:

### 1. Start an MCP Server
Run the MCP server with an accessible URL. For example, start the **Math Tool Server** located in `contrib/mcp/server`:

```sh
uv run server.py
```

This will start the MCP server at the following URL:
**`http://0.0.0.0:8080`**

### 2. Run the Blueberry Service Tool
Make sure the **Blueberry Service Tool** is running by executing the following command in the **Blueberry-tools-service** root folder:

```sh
make run
```

### 3. Upload a Demo MCP Tool
Open the API documentation at:

```
http://localhost:8000/docs
```

Use the **POST** `/file/json/` API to upload a demo MCP tool from:

```
contrib/mcp/demo_tool/demo_mcp_server.json
```

Make sure to use the **server name `math.py`**.
This will add all the tools that exist in the Math MCP server.

### 4. Execute the Tool
To execute the tool, combine the **server name** and **tool name** to create a filename (e.g., `math_add.py`).
Use the **POST** `/excute/` Pass the required parameters in JSON format. Example:

```json
{
  "a": 5,
  "b": 5
}
```

## MCP Server Configuration

### MCP Server URL
The MCP server URL is retrieved from the **`url`** field in the JSON.
If not provided, it defaults to the environment variable:

```sh
MCP_SERVER_URL
```

### Adding a Single Tool from the MCP Server
If you only want to add a **single tool** from the MCP server, include the tool name in the metadata.
Refer to this example:

```
contrib/mcp/demo_tool/demo_add_single_tool.json
```

### Content Field
- The **`content`** field is **optional**.
- If provided, it **overwrites** the automatically generated content from the MCP server.
