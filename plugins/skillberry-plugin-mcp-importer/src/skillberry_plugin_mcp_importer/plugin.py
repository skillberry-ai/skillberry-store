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


def _extract_error_detail(url: str, exc: Exception) -> str:
    """Return a human-readable error message, unwrapping ExceptionGroup if needed."""
    # Python 3.11+ wraps anyio task-group errors in ExceptionGroup.
    # Unwrap one level to surface the real cause.
    inner: Exception = exc
    subs = getattr(exc, "exceptions", None)
    if subs:
        inner = subs[0]

    msg = str(inner)

    # Give a targeted hint when the server returned 404 — the user almost
    # certainly provided a base URL instead of the SSE endpoint path.
    if "404" in msg:
        return (
            f"MCP server returned 404 for '{url}'. "
            "Make sure the URL points to the SSE endpoint "
            "(e.g. http://host:port/sse), not the server root."
        )

    return f"Failed to connect to MCP server: {msg}"


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

    @staticmethod
    def _skill_name_from_url(mcp_url: str) -> str:
        """Derive a skill name from a MCP URL, e.g. 'localhost_3001_sse'."""
        from urllib.parse import urlparse
        parsed = urlparse(mcp_url)
        parts = [parsed.hostname or "mcp"]
        if parsed.port:
            parts.append(str(parsed.port))
        path = parsed.path.strip("/").replace("/", "_")
        if path:
            parts.append(path)
        raw = "_".join(parts)
        return "".join(c if c.isalnum() or c == "_" else "_" for c in raw)

    @staticmethod
    def _hostname_from_url(mcp_url: str) -> str:
        """Extract the hostname from a MCP URL, e.g. 'localhost', 'api.acme.com'."""
        from urllib.parse import urlparse
        return urlparse(mcp_url).hostname or "mcp"

    async def _import_tools(
        self,
        mcp_url: str,
        create_skill: bool = True,
        skill_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Connect to the MCP server at mcp_url, list all tools, create each in the store.

        Returns a summary dict with keys:
          - imported: int          number of successfully imported tools
          - tools: list            [{"name": ..., "uuid": ...}, ...]
          - failed: list           [{"name": ..., "error": ...}, ...]
          - skill: dict or None    {"name": ..., "uuid": ...} if create_skill=True
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

        skill: Optional[Dict[str, Any]] = None
        if create_skill and imported:
            name = skill_name or self._skill_name_from_url(mcp_url)
            tool_uuids = [t["uuid"] for t in imported]
            try:
                skill_result = self.store.create_skill(
                    {
                        "name": name,
                        "description": f"Tools imported from {mcp_url}",
                        "tool_uuids": tool_uuids,
                    }
                )
                skill = {"name": skill_result["name"], "uuid": skill_result["uuid"]}
            except Exception as exc:
                logger.warning(f"Failed to create skill '{name}': {exc}")

        return {
            "success": len(failed) == 0 and len(imported) > 0,
            "imported": len(imported),
            "tools": imported,
            "failed": failed,
            "skill": skill,
        }

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class ImportRequest(BaseModel):
            mcp_url: str
            create_skill: bool = True
            skill_name: Optional[str] = None

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
                return await self._import_tools(
                    url,
                    create_skill=request.create_skill,
                    skill_name=request.skill_name,
                )
            except Exception as exc:
                logger.error(
                    f"Failed to import from MCP server '{url}': {exc}", exc_info=True
                )
                detail = _extract_error_detail(url, exc)
                raise HTTPException(status_code=502, detail=detail)

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
                            },
                            "create_skill": {
                                "type": "boolean",
                                "default": True,
                                "description": "Automatically create a skill grouping all imported tools (default: true)",
                            },
                            "skill_name": {
                                "type": "string",
                                "description": "Name for the auto-created skill (default: derived from MCP URL)",
                            },
                        },
                        "required": ["mcp_url"],
                    },
                }
            ],
        }

# Made with Bob
