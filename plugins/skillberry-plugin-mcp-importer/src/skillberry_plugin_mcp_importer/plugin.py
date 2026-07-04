"""
Skillberry Plugin MCP Importer - imports tools from a customer MCP server via SSE.

Connects to the MCP server, lists its tools, and creates each in the store as
an "mcp"-packaged tool. Optionally groups all imported tools into a single
skill. No LLM involved.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

from skillberry_plugin_sdk import PluginLifecycleBase

logger = logging.getLogger(__name__)


def _mcp_content(tool_dict: Dict[str, Any]) -> str:
    """Stub Python module body derived from a MCP tool's inputSchema.

    Ported from ``skillberry_store.fast_api.server_utils.mcp_content`` so the
    plugin does not import from the store package. The MCP packaging format
    only needs a callable signature and docstring for tooling that inspects
    the module; execution goes through the MCP tunnel.
    """
    input_schema = tool_dict.get("inputSchema") or {}
    properties = input_schema.get("properties", {}) or {}
    required = input_schema.get("required", []) or []
    parameters = {
        "type": "object",
        "properties": {
            k: {"type": v.get("type", "string"), "description": f"The {k} parameter."}
            for k, v in properties.items()
        },
        "required": required,
    }
    param_list = ", ".join(
        f"{k}: {v['type']}" for k, v in parameters["properties"].items()
    )
    content_lines = [
        f"def {tool_dict['name']}({param_list}):",
        '    """',
        f"    {tool_dict.get('description', '') or ''}",
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
    return "\n".join(line for line in content_lines if line.strip())


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


class SkillberryPluginMcpImporter(PluginLifecycleBase):
    """Plugin that imports all tools exposed by a customer MCP SSE server."""

    manifest_path = "manifest.yaml"

    async def on_start(self) -> None:  # noqa: D401 - simple override
        """No heavy initialization required."""
        return None

    async def is_ready(self) -> Dict[str, Any]:
        return {"ready": True, "missing_config": []}

    # ── URL helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _skill_name_from_url(mcp_url: str) -> str:
        """Derive a skill name from a MCP URL, e.g. 'localhost_3001_sse'."""
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
        return urlparse(mcp_url).hostname or "mcp"

    # ── Store write helpers ──────────────────────────────────────────────────
    #
    # The SDK's StoreClient does not provide async equivalents for the SBS
    # ``POST /tools/`` (multipart file upload) or ``POST /skills/`` (query-arg
    # payload) endpoints. Both are called with an async httpx client directly,
    # reusing the StoreClient's base URL and auth headers.
    #
    # TODO(sdk): when the SDK gains ``create_tool``/``create_skill`` helpers
    # (multipart + query-arg aware), replace these with the SDK methods.

    async def _create_tool(
        self,
        data: Dict[str, Any],
        module_content: bytes,
        module_filename: str,
    ) -> Dict[str, Any]:
        """POST /tools/ with tool metadata as query params and module as multipart file."""
        store = self.store
        url = f"{store.base_url}/tools/"
        headers = {k: v for k, v in store._headers().items() if k != "Accept"}
        headers["Accept"] = "application/json"
        # ToolSchema fields are sent as query params. Complex fields (params,
        # packaging_params, tags) must be JSON-encoded strings for FastAPI's
        # Query() parsing.
        import json as _json
        params: Dict[str, Any] = {}
        for k, v in data.items():
            if v is None:
                continue
            if isinstance(v, (dict, list)):
                params[k] = _json.dumps(v)
            else:
                params[k] = v
        files = {"module": (module_filename, module_content, "text/x-python")}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, params=params, files=files, headers=headers)
            r.raise_for_status()
            return r.json()

    async def _create_skill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST /skills/ with skill metadata as query params."""
        store = self.store
        url = f"{store.base_url}/skills/"
        headers = store._headers()
        import json as _json
        params: Dict[str, Any] = {}
        for k, v in data.items():
            if v is None:
                continue
            if isinstance(v, (dict, list)):
                params[k] = _json.dumps(v)
            else:
                params[k] = v
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, params=params, headers=headers)
            r.raise_for_status()
            return r.json()

    # ── Core import logic ────────────────────────────────────────────────────

    async def _import_tools(
        self,
        mcp_url: str,
        create_skill: bool = True,
        skill_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
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

        hostname = self._hostname_from_url(mcp_url)
        resolved_skill_name = skill_name or self._skill_name_from_url(mcp_url)

        tool_tags: List[str] = ["mcp", hostname]
        if create_skill:
            tool_tags.append(f"skill:{resolved_skill_name}")
        for tag in (tags or []):
            if tag and tag not in tool_tags:
                tool_tags.append(tag)

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
                "tags": tool_tags,
            }
            stub = _mcp_content(vars(tool))
            try:
                result = await self._create_tool(
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
            tool_uuids = [t["uuid"] for t in imported]
            skill_tags: List[str] = ["mcp", "imported", hostname]
            for tag in (tags or []):
                if tag and tag not in skill_tags:
                    skill_tags.append(tag)
            try:
                skill_result = await self._create_skill(
                    {
                        "name": resolved_skill_name,
                        "description": f"Tools imported from {mcp_url}",
                        "tool_uuids": tool_uuids,
                        "tags": skill_tags,
                    }
                )
                skill = {"name": skill_result["name"], "uuid": skill_result["uuid"]}
            except Exception as exc:
                logger.warning(f"Failed to create skill '{resolved_skill_name}': {exc}")

        return {
            "success": len(failed) == 0 and len(imported) > 0,
            "imported": len(imported),
            "tools": imported,
            "failed": failed,
            "skill": skill,
        }

    # ── HTTP API ─────────────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class ImportRequest(BaseModel):
            mcp_url: str
            create_skill: bool = True
            skill_name: Optional[str] = None
            tags: Optional[List[str]] = None

        @router.post("/import-tools")
        async def import_tools(payload: ImportRequest):
            """Import all tools from the given MCP SSE server into the store."""
            url = (payload.mcp_url or "").strip()
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
                    create_skill=payload.create_skill,
                    skill_name=payload.skill_name,
                    tags=payload.tags,
                )
            except Exception as exc:
                logger.error(
                    f"Failed to import from MCP server '{url}': {exc}", exc_info=True
                )
                detail = _extract_error_detail(url, exc)
                raise HTTPException(status_code=502, detail=detail)

        return router

# Made with Bob
