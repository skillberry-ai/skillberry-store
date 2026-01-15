from mcp import ClientSession
from mcp.client.sse import sse_client
from fastapi import HTTPException

import os


def mcp_content(tool_dict: dict) -> str:
    """
    Returns mcp tool 'content' calculated out from its function signature and parameter definition.

    This utility is being called by the execution module.

    Parameters:
        tool_dict (dict): The tool information retrieved from the MCP server.
    """
    input_schema = tool_dict.get("inputSchema", {})
    parameters = {
        "type": "object",
        "properties": {
            k: {"type": v["type"], "description": f"The {k} parameter."}
            for k, v in input_schema.get("properties", {}).items()
        },
        "required": input_schema.get("required", []),
    }
    param_list = ", ".join(
        [f"{k}: {v['type']}" for k, v in parameters["properties"].items()]
    )

    content_lines = [
        f"def {tool_dict['name']}({param_list}):",
        '    """',
        f"    {tool_dict['description']}",
        (
            ""
            if not parameters["properties"]
            else "\n".join(
                [
                    "    Parameters:",
                    *[
                        f"        {k} ({v['type']}): {v['description']}"
                        for k, v in parameters["properties"].items()
                    ],
                ]
            )
        ),
        '    """',
    ]
    content = "\n".join(line for line in content_lines if line.strip())

    return content


def mcp_json_converter(tool: dict, manifest_as_dict: dict) -> dict:
    """
    Converts an MCP tool JSON into the required manifest format by adding
    description and parameters.

    Parameters:
        tool (dict): The tool information retrieved from the MCP server.
        manifest_as_dict (dict): The base JSON with manifest information.

    Returns:
        dict: A JSON object formatted as per the original structure.
    """
    input_schema = tool.get("inputSchema", {})
    parameters = {
        "type": "object",
        "properties": {
            k: {"type": v["type"], "description": f"The {k} parameter."}
            for k, v in input_schema.get("properties", {}).items()
        },
        "required": input_schema.get("required", []),
    }

    generated_json = {"description": tool["description"], "params": parameters}

    return generated_json


async def get_mcp_tools(manifest_as_dict: dict) -> list:
    """
    Retrieves tool information from the MCP server based on the provided manifest. If manifest
    contains name then tool with that name should be returned.

    Parameters:
        manifest_as_dict (dict): The manifest containing MCP server details, including the URL and tool name.

    Returns:
        list: A list of dictionaries representing the retrieved tools, or None if no tools found.
    """
    async with sse_client(manifest_as_dict.get("mcp_url", {})) as (read, write):
        async with ClientSession(read, write) as session:
            tool_name = manifest_as_dict.get("name", {})
            await session.initialize()

            tools = await session.list_tools()
            # TODO:
            if not tools:
                return None
            # Find matching tool by name
            if tool_name:
                for tool in tools.tools:
                    if tool.name == manifest_as_dict.get("name", {}):
                        return [tool]
                return None
            else:
                # add: 'if tools.tools and len(tools.tools) > 0 else None' ?
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
