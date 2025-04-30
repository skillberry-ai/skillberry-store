import logging

from typing import Any
from mcp import server, types
from mcp.client.session import ClientSession
from tools.configure import configure_logging
from dataclasses import dataclass
from fastapi import FastAPI


@dataclass
class ToolMapping:
    server_name: str
    client: ClientSession
    tool: types.Tool


class MCPToBTSProxy(server.Server):
    """An MCP Proxy Server that convert the requests to BTS."""

    def __init__(self, app: FastAPI):
        super().__init__("MCP-BTS Proxy")
        self._register_request_handlers()
        configure_logging()
        self.app = app
        self.logger = logging.getLogger(__name__)

    async def _list_tools(self, _: Any) -> types.ServerResult:
        """Send a list of the tools from BTS."""
        manifests_list = self.app.handle_get_manifests()

        self.logger.info(f"Found {len(manifests_list)} manifests")

        tools = []
        for manifest_dict in manifests_list:
            try:
                tool = self.manifest_to_tool(manifest_dict)
                tools.append(tool)
            except Exception as e:
                self.logger.warning(f"Failed to convert manifest to tool: {e}")

        return types.ListToolsResult(tools=tools)

    async def _call_tool(self, req: types.CallToolRequest) -> types.ServerResult:
        """Invoke a tool using the appropriate manifest in BTS."""
        result = await self.app.handle_execute_manifest(
            req.params.name, req.params.arguments
        )
        self.logger.info(f"result {result}")

        return types.CallToolResult(
            content=[types.TextContent(type="text", text=str(result))]
        )

    def _register_request_handlers(self) -> None:
        """Dynamically registers handlers for all MCP requests."""

        self.request_handlers[types.ListToolsRequest] = self._list_tools
        self.request_handlers[types.CallToolRequest] = self._call_tool

    def manifest_to_tool(self, manifest: dict[str, Any]) -> types.Tool:
        # Clean up extras before unpacking
        extras = manifest.copy()
        for key in ["name", "description", "params"]:
            extras.pop(key, None)

        return types.Tool(
            name=str(manifest["name"]),
            description=manifest.get("description"),
            inputSchema=manifest["params"],
            **extras,
        )

    def tool_to_manifest(self, tool: types.Tool) -> dict[str, Any]:
        # Start with required manifest fields
        manifest = {
            "name": tool.name,
            "description": tool.description,
            "params": tool.inputSchema,
            "uid": tool.name,  # or generate something else
        }

        # Add extra fields (everything other than name/description/inputSchema)
        extras = tool.model_dump(exclude={"name", "description", "inputSchema"})
        manifest.update(extras)

        return manifest
