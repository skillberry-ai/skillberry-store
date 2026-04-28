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


def mcp_content_from_manifest(tool_dict: dict) -> str:
    """
    Returns the same stub as mcp_content() but reads from the stored manifest format
    (tool_dict["params"]["properties"]) instead of the MCP server response format
    (tool_dict["inputSchema"]["properties"]).  Using this avoids an extra SSE round-trip
    to the MCP server just to build the stub.

    Parameters:
        tool_dict (dict): The stored tool manifest dict (ToolSchema format).
    """
    params = tool_dict.get("params") or {}
    properties = params.get("properties") or {}
    required = params.get("required") or []

    param_list = ", ".join(
        f"{k}: {v.get('type', 'str')}" for k, v in properties.items()
    )

    content_lines = [
        f"def {tool_dict['name']}({param_list}):",
        '    """',
        f"    {tool_dict.get('description', '')}",
        (
            ""
            if not properties
            else "\n".join(
                [
                    "    Parameters:",
                    *[
                        f"        {k} ({v.get('type', 'str')}): {v.get('description', f'The {k} parameter.')}"
                        for k, v in properties.items()
                    ],
                ]
            )
        ),
        '    """',
    ]
    return "\n".join(line for line in content_lines if line.strip())


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
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    mcp_url = manifest_as_dict.get("mcp_url", {})
    logger.info(f"[get_mcp_tools] Starting - Connecting to MCP server at: {mcp_url}")
    logger.debug(f"[get_mcp_tools] Manifest dict: {manifest_as_dict}")

    try:
        logger.info(f"[get_mcp_tools] Creating SSE client connection...")
        async with sse_client(mcp_url, sse_read_timeout=30) as (read, write):
            logger.info(
                f"[get_mcp_tools] SSE client connected, creating ClientSession..."
            )
            async with ClientSession(read, write) as session:
                tool_name = manifest_as_dict.get("name", {})
                logger.info(
                    f"[get_mcp_tools] ClientSession created, tool_name: {tool_name}"
                )

                # Add timeout for initialization
                logger.info("[get_mcp_tools] Initializing MCP session...")
                await asyncio.wait_for(session.initialize(), timeout=10.0)
                logger.info("[get_mcp_tools] MCP session initialized successfully")

                # Add timeout for listing tools
                logger.info("[get_mcp_tools] Listing tools from MCP server...")
                tools = await asyncio.wait_for(session.list_tools(), timeout=10.0)
                logger.info(
                    f"[get_mcp_tools] Retrieved {len(tools.tools) if tools and tools.tools else 0} tools from MCP server"
                )

                # TODO:
                if not tools:
                    logger.warning("[get_mcp_tools] No tools returned from MCP server")
                    return None
                # Find matching tool by name
                if tool_name:
                    logger.info(f"[get_mcp_tools] Searching for tool: {tool_name}")
                    for tool in tools.tools:
                        if tool.name == manifest_as_dict.get("name", {}):
                            logger.info(
                                f"[get_mcp_tools] Found matching tool: {tool.name}"
                            )
                            return [tool]
                    logger.warning(
                        f"[get_mcp_tools] Tool '{tool_name}' not found in MCP server"
                    )
                    return None
                else:
                    logger.info(
                        f"[get_mcp_tools] Returning all {len(tools.tools)} tools"
                    )
                    # add: 'if tools.tools and len(tools.tools) > 0 else None' ?
                    return tools.tools
    except asyncio.TimeoutError as te:
        logger.error(
            f"[get_mcp_tools] Timeout connecting to MCP server at {mcp_url}: {te}"
        )
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to MCP server at {mcp_url}. Please verify the server is running and accessible.",
        )
    except Exception as e:
        logger.error(
            f"[get_mcp_tools] Error connecting to MCP server at {mcp_url}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Error connecting to MCP server: {str(e)}"
        )


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
