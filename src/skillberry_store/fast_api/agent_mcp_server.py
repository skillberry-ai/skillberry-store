"""Curated Agent MCP Server for Skillberry Store.

Exposes a hand-picked set of LLM-friendly tools over SSE on its own port.
Every tool here is a thin proxy to the local FastAPI backend (same process,
different port) so validation, observability, and persistence stay in one
place — the REST layer. The curation value is the smaller surface area and
better names/docstrings, not reimplemented logic.
"""

import json
import logging
import threading
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def create_agent_mcp_server(app, port: int = 9999):
    """Build and start the curated Agent MCP server in a background thread.

    Args:
        app: The SBS FastAPI application. Used to read the backend port so
            the proxy always hits the same process (even when SBS_PORT is
            overridden).
        port: TCP port for the curated SSE endpoint.

    Returns:
        The FastMCP instance (already serving).
    """
    mcp = FastMCP(name="skillberry-agent", port=port)

    backend_port = app.settings.sbs_port
    base_url = f"http://127.0.0.1:{backend_port}"
    client_timeout = httpx.Timeout(60.0, connect=5.0)

    def _request(method: str, path: str, **kwargs) -> str:
        """Call the local FastAPI and return the response body as text.

        Returns the raw JSON string on success and a JSON-encoded error
        envelope on failure — agents parse MCP results as strings either
        way, so the extra quoting isn't useful.
        """
        try:
            with httpx.Client(base_url=base_url, timeout=client_timeout) as c:
                r = c.request(method, path, **kwargs)
            if r.status_code >= 400:
                return json.dumps({
                    "error": True,
                    "status": r.status_code,
                    "detail": r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else r.text,
                })
            return r.text
        except Exception as e:
            return json.dumps({"error": True, "detail": str(e)})

    def _resolve_tool_uuids(tool_names: List[str]) -> List[str]:
        """Look up tool UUIDs by name via GET /tools/{name}."""
        uuids: List[str] = []
        with httpx.Client(base_url=base_url, timeout=client_timeout) as c:
            for n in tool_names:
                r = c.get(f"/tools/{n}")
                if r.status_code == 200:
                    uuids.append(r.json().get("uuid", ""))
                else:
                    raise ValueError(f"Tool '{n}' not found")
        return uuids

    def _resolve_skill_uuid(skill_name: str) -> str:
        """Look up a skill UUID by name via GET /skills/{name}."""
        with httpx.Client(base_url=base_url, timeout=client_timeout) as c:
            r = c.get(f"/skills/{skill_name}")
        if r.status_code != 200:
            raise ValueError(f"Skill '{skill_name}' not found")
        return r.json().get("uuid", "")

    # ---- Tools ----

    @mcp.tool()
    def list_tools() -> str:
        """List every tool in the store (name, description, state, tags)."""
        return _request("GET", "/tools/")

    @mcp.tool()
    def get_tool(name: str) -> str:
        """Get a tool's full metadata manifest by name."""
        return _request("GET", f"/tools/{name}")

    @mcp.tool()
    def get_tool_code(name: str) -> str:
        """Get a tool's Python source code."""
        return _request("GET", f"/tools/{name}/module")

    @mcp.tool()
    def create_tool(code: str, filename: str, tool_name: Optional[str] = None) -> str:
        """Create a new tool by uploading Python source with a docstring.

        The store parses the function's docstring to extract description and
        parameter schema, so the code must contain a function with a
        well-formed docstring (Google, NumPy, or Sphinx style).

        Args:
            code: The full Python source (one or more functions).
            filename: Name for the uploaded file, e.g. "my_tool.py".
            tool_name: Optional specific function to register. Defaults to
                the first function in the file.
        """
        params: Dict[str, Any] = {}
        if tool_name:
            params["tool_name"] = tool_name
        return _request(
            "POST",
            "/tools/add",
            params=params,
            files={"tool": (filename, code.encode("utf-8"), "text/x-python")},
        )

    @mcp.tool()
    def execute_tool(name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Execute a tool by name with the given parameters.

        Args:
            name: The tool name.
            parameters: Keyword arguments passed to the tool's function.
        """
        return _request("POST", f"/tools/{name}/execute", json=parameters or {})

    @mcp.tool()
    def search_tools(query: str, max_results: int = 5) -> str:
        """Semantic search over tool descriptions.

        Args:
            query: The search query.
            max_results: Maximum number of results.
        """
        return _request(
            "GET",
            "/search/tools",
            params={"search_term": query, "max_number_of_results": max_results},
        )

    # ---- Skills ----

    @mcp.tool()
    def list_skills() -> str:
        """List every skill in the store."""
        return _request("GET", "/skills/")

    @mcp.tool()
    def get_skill(name: str) -> str:
        """Get a skill's full manifest by name."""
        return _request("GET", f"/skills/{name}")

    @mcp.tool()
    def create_skill(
        name: str,
        description: str,
        tool_names: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new skill. Resolves tool names to UUIDs automatically.

        Args:
            name: The skill name.
            description: Human-readable description.
            tool_names: Optional tool names to include — each is resolved to
                the corresponding tool UUID before creation.
            tags: Optional tags.
        """
        try:
            tool_uuids = _resolve_tool_uuids(tool_names or [])
        except ValueError as e:
            return json.dumps({"error": True, "detail": str(e)})
        params: List[tuple] = [
            ("name", name),
            ("description", description),
            ("version", "1.0.0"),
            ("state", "approved"),
        ]
        for u in tool_uuids:
            params.append(("tool_uuids", u))
        for t in tags or []:
            params.append(("tags", t))
        return _request("POST", "/skills/", params=params)

    @mcp.tool()
    def search_skills(query: str, max_results: int = 5) -> str:
        """Semantic search over skill descriptions.

        Args:
            query: The search query.
            max_results: Maximum number of results.
        """
        return _request(
            "GET",
            "/search/skills",
            params={"search_term": query, "max_number_of_results": max_results},
        )

    # ---- Virtual MCP servers ----

    @mcp.tool()
    def list_vmcp_servers() -> str:
        """List every Virtual MCP Server in the store."""
        return _request("GET", "/vmcp_servers/")

    @mcp.tool()
    def create_vmcp_server(
        name: str,
        skill_name: str,
        port: Optional[int] = None,
    ) -> str:
        """Create and start a Virtual MCP Server for a skill.

        Args:
            name: Name for the new VMCP server.
            skill_name: Skill whose tools/snippets the VMCP will expose.
                Resolved to skill_uuid automatically.
            port: Optional TCP port; auto-assigned if omitted.
        """
        try:
            skill_uuid = _resolve_skill_uuid(skill_name)
        except ValueError as e:
            return json.dumps({"error": True, "detail": str(e)})
        params: List[tuple] = [
            ("name", name),
            ("description", f"VMCP server for skill '{skill_name}'"),
            ("version", "1.0.0"),
            ("state", "approved"),
            ("skill_uuid", skill_uuid),
        ]
        if port is not None:
            params.append(("port", port))
        return _request("POST", "/vmcp_servers/", params=params)

    @mcp.tool()
    def delete_vmcp_server(name: str) -> str:
        """Stop and delete a Virtual MCP Server by name."""
        return _request("DELETE", f"/vmcp_servers/{name}")

    # ---- Start the server ----

    def _start():
        logger.info(f"Starting Agent MCP server on port {port}")
        sse_app = mcp.sse_app()
        sse_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            expose_headers=["*"],
        )
        uvicorn.run(sse_app, host="127.0.0.1", port=port, log_level="info")

    threading.Thread(target=_start, daemon=True).start()
    logger.info(f"Agent MCP server started on port {port}")
    return mcp
