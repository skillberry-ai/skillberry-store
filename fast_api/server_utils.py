from mcp import ClientSession
from mcp.client.sse import sse_client
from fastapi import HTTPException

import os
def mcp_json_converter(tool: dict, file_json: dict)-> dict:
    """
    Converts an MCP tool JSON into the required format.

    Parameters:
        tool (dict): The tool information retrieved from the MCP server.
        file_json (dict): The base JSON with metadata information.

    Returns:
        dict: A JSON object formatted as per the original structure.
    """
    input_schema = tool.get("inputSchema", {})
    parameters = {
        "type": "object",
        "properties": {
            k: {
                "type": v["type"],
                "description": f"The {k} parameter."
            } for k, v in input_schema.get("properties", {}).items()
        },
        "required": input_schema.get("required", [])
    }
    param_list = ", ".join([f"{k}: {v['type']}" for k, v in parameters["properties"].items()])

    content_lines = [
        f"def {tool['name']}({param_list}):",
        "    \"\"\"",
        f"    {tool['description']}",
        "" if not parameters["properties"] else "\n".join(
            [
                "    Parameters:",
                *[f"        {k} ({v['type']}): {v['description']}" for k, v in parameters["properties"].items()]
            ]
        ),
        "    \"\"\""
    ]
    content = "\n".join(line for line in content_lines if line.strip())

    generated_json = {
        "content": file_json.get("content", content),  # Allow override content from file json
        "description": tool["description"],
        "metadata": {
            "programming_language": file_json.get("metadata", {}).get("programming_language", "python"),
            "packaging_format": "mcp",
            "url": file_json.get("metadata", {}).get("url", ""),
            "name": tool["name"],
            "description": tool["description"],
            "parameters": parameters,
            "state": file_json.get("metadata", {}).get("state", "approved")
        }
    }
    return generated_json

async def get_mcp_tools(file_metadata: dict)-> list:
    """
    Retrieves tool information from the MCP server based on the provided metadata.

    Parameters:
        file_metadata (dict): The metadata containing MCP server details, including the URL and tool name.

    Returns:
        list: A list of dictionaries representing the retrieved tools, or raises an HTTPException if no tools are found.
    """
    async with sse_client(file_metadata.get("url",{})) as (read, write):
        async with ClientSession(read, write) as session:
            tool_name =file_metadata.get("name",{})
            await session.initialize()

            tools = await session.list_tools()
            if not tools:
                raise HTTPException(status_code=500, detail="No tools retrieved from MCP.")
            # Find matching tool by name
            if tool_name:
                for tool in tools.tools:
                    if tool.name == file_metadata.get("name", {}):
                        return [tool]
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

            return tools.tools

def generate_mcp_filename(file_name: str, tool_name: str) -> str:
    """
    Generates a new filename by combining the given file name and tool name.

    Parameters:
        file_name (str): The original file name.
        tool_name (str): The tool name to append.

    Returns:
        str: A new filename with the server and tool name included.
    """
    server_name, ext = os.path.splitext(file_name)
    return f"{server_name}_{tool_name}{ext}"
