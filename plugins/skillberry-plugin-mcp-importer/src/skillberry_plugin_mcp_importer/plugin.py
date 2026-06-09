"""
Skillberry Plugin MCP Importer - imports tools from a customer MCP server via SSE.
No LLM involved. Connects to the MCP server, lists its tools, creates each in the store.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.sse import sse_client

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_store.fast_api.server_utils import mcp_content

logger = logging.getLogger(__name__)


class SkillberryPluginMcpImporter(PluginBase):
    """Plugin that imports all tools exposed by a customer MCP SSE server."""

    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="MCP Importer",
            version="0.1.0",
            description="Import tools from a customer MCP server via SSE",
            plugin_type=PluginType.IMPORTER,
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def is_enabled(self) -> bool:
        return True

    def get_status_message(self) -> str:
        return "Ready"

    async def _import_tools(self, mcp_url: str) -> Dict[str, Any]:
        """
        Connect to the MCP server at mcp_url, list all tools, create each in the store.

        Returns a summary dict with keys:
          - imported: int   number of successfully imported tools
          - tools: list     [{"name": ..., "uuid": ...}, ...]
          - failed: list    [{"name": ..., "error": ...}, ...]
        """
        async with sse_client(mcp_url, sse_read_timeout=30) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=10.0)
                tools_result = await asyncio.wait_for(session.list_tools(), timeout=10.0)
                tools: List[Any] = tools_result.tools or []

        imported: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []

        for tool in tools:
            input_schema = tool.inputSchema or {}
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])
            params = {
                "type": "object",
                "properties": {
                    k: {
                        "type": v.get("type", "string"),
                        "description": v.get("description", f"The {k} parameter."),
                    }
                    for k, v in properties.items()
                },
                "required": required,
            }
            data = {
                "name": tool.name,
                "description": tool.description or "",
                "packaging_format": "mcp",
                "packaging_params": {
                    "mcp_url": mcp_url,
                    "mcp_tool_name": tool.name,
                },
                "params": params,
                "programming_language": "python",
            }
            stub = mcp_content(vars(tool))
            try:
                result = self.store.create_tool(
                    data,
                    module_content=stub.encode(),
                    module_filename=f"{tool.name}.py",
                )
                imported.append({"name": result["name"], "uuid": result["uuid"]})
            except Exception as exc:
                logger.warning(f"Failed to import tool '{tool.name}': {exc}")
                failed.append({"name": tool.name, "error": str(exc)})

        return {"imported": len(imported), "tools": imported, "failed": failed}

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class ImportRequest(BaseModel):
            mcp_url: str

        @router.post("/import-tools")
        async def import_tools(request: ImportRequest):
            """Import all tools from the given MCP SSE server into the store."""
            url = (request.mcp_url or "").strip()
            if not url:
                raise HTTPException(status_code=400, detail="mcp_url is required")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise HTTPException(
                    status_code=400,
                    detail="mcp_url must start with http:// or https://",
                )
            try:
                return await self._import_tools(url)
            except Exception as exc:
                logger.error(
                    f"Failed to import from MCP server '{url}': {exc}", exc_info=True
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to MCP server: {str(exc)}",
                )

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "DownloadIcon",
            "color": "#6F42C1",
            "actions": [
                {
                    "label": "Import MCP Tools",
                    "endpoint": "/plugins/mcp-importer/import-tools",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "mcp_url": {
                                "type": "string",
                                "description": "SSE URL of the MCP server to import tools from",
                            }
                        },
                        "required": ["mcp_url"],
                    },
                }
            ],
        }

# Made with Bob
