"""External MCPs API — manage imported MCP servers and their primitives."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Request

from skillberry_store.modules.external_mcp_manager import (
    ExternalMCPManager,
    normalize_mcp_input,
)

logger = logging.getLogger(__name__)


def _manager(request: Request) -> ExternalMCPManager:
    mgr: Optional[ExternalMCPManager] = getattr(
        request.app.state, "external_mcp_manager", None
    )
    if mgr is None:
        raise HTTPException(
            status_code=503,
            detail="External MCP manager is not initialized",
        )
    return mgr


def register_external_mcps_api(app: FastAPI, tags: str = "external_mcps") -> None:
    """Register the external MCPs REST endpoints."""

    @app.get("/external-mcps", tags=[tags])
    async def list_external_mcps(request: Request) -> List[Dict[str, Any]]:
        """List every imported external MCP server with status + tool count."""
        return _manager(request).list_servers()

    @app.post("/external-mcps", tags=[tags])
    async def add_external_mcps(
        request: Request,
        config: Any = Body(..., description="Any of the 5 supported input shapes."),
    ) -> Dict[str, Any]:
        """
        Register and start one or more external MCP servers.

        Accepts the standard Claude-Desktop-style `{"mcpServers": {...}}`,
        a bare name→entry dict, a list of entries, a single entry with
        `name`, or `{"source_url": "..."}` to fetch a config from a URL.
        Secrets in the posted body are persisted to disk as-is (plaintext,
        matching existing `ai_features/settings.json` convention).
        """
        try:
            entries = normalize_mcp_input(config)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        mgr = _manager(request)
        results: List[Dict[str, Any]] = []
        for entry in entries:
            try:
                result = await mgr.start(entry, persist=True)
            except Exception as e:
                logger.error("Failed to register external MCP %s: %s", entry.get("name"), e)
                result = {"name": entry.get("name"), "status": "error", "error": str(e)}
            results.append(result)
        return {"count": len(results), "results": results}

    @app.delete("/external-mcps/{name}", tags=[tags])
    async def remove_external_mcp(request: Request, name: str) -> Dict[str, Any]:
        """Stop the server, delete its config, and delete every imported primitive.

        Composites that depended on those primitives are NOT deleted — they
        are left as regular tools and will be flagged `state="broken"` with
        `broken_reason="dep_missing:..."` by the universal health pass.
        """
        mgr = _manager(request)
        try:
            return await mgr.remove(name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/external-mcps/{name}/restart", tags=[tags])
    async def restart_external_mcp(request: Request, name: str) -> Dict[str, Any]:
        """Stop and restart the server; reconciles primitives against remote list_tools()."""
        mgr = _manager(request)
        try:
            return await mgr.restart(name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/external-mcps/{name}/remote-tools", tags=[tags])
    async def list_remote_tools(request: Request, name: str) -> List[Dict[str, Any]]:
        """Pass-through `list_tools()` on the live session — useful for UI preview."""
        mgr = _manager(request)
        try:
            return await mgr.list_remote_tools(name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=409, detail=str(e))

    @app.get("/external-mcps/{name}/dependents", tags=[tags])
    async def list_dependents(request: Request, name: str) -> Dict[str, Any]:
        """Tools that will transition to `state="broken"` if this server is removed."""
        mgr = _manager(request)
        dependents = mgr.find_dependents(name)
        return {"name": name, "dependents": dependents}

    @app.get("/external-mcps/{name}", tags=[tags])
    async def get_external_mcp(request: Request, name: str) -> Dict[str, Any]:
        """Return config + status for a single external MCP."""
        mgr = _manager(request)
        server = mgr.get_server(name)
        if server is None:
            raise HTTPException(status_code=404, detail=f"unknown external MCP: {name}")
        return server
