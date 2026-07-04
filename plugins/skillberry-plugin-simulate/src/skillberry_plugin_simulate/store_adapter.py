"""Adapter that widens the SDK StoreClient with vMCP CRUD used by the orchestrator.

The SDK's StoreClient only exposes generic ``get``/``post`` plus a few
narrow helpers. The simulate orchestrator needs vMCP CRUD and create/delete
helpers for tools and skills; this thin wrapper maps those to the SBS REST
API without changing the SDK surface.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import httpx

from skillberry_plugin_sdk import StoreClient


class SimulateStoreAdapter:
    """Wraps an SDK StoreClient with the extra methods the orchestrator uses."""

    def __init__(self, store: StoreClient):
        self._store = store

    # Existing sync-friendly methods delegate to the SDK client.
    async def get_skill(self, uuid: str) -> Optional[Dict[str, Any]]:
        return await self._store.get_skill(uuid)

    async def get_tool(self, uuid: str) -> Optional[Dict[str, Any]]:
        return await self._store.get_tool(uuid)

    # vMCPs ------------------------------------------------------------------
    async def get_vmcp(self, uuid_or_name: str) -> Optional[Dict[str, Any]]:
        return await self._store.get(f"/vmcp_servers/{uuid_or_name}")

    async def list_vmcps(self) -> List[Dict[str, Any]]:
        result = await self._store.get("/vmcp_servers/")
        if result is None:
            return []
        if isinstance(result, dict):
            return (
                result.get("virtual_mcp_servers")
                or result.get("vmcp_servers")
                or list(result.values())
            )
        return result  # type: ignore[return-value]

    async def create_vmcp(
        self, manifest: Dict[str, Any], *, env_id: str = ""
    ) -> Dict[str, Any]:
        # SBS's create_vmcp_server uses query params for the schema fields.
        headers = {"Accept": "application/json"}
        if self._store.token:
            headers["Authorization"] = f"Bearer {self._store.token}"
        if env_id:
            headers["x-skillberry-env-id"] = env_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._store.base_url}/vmcp_servers/",
                params=_flatten_query(manifest),
                headers=headers,
            )
            r.raise_for_status()
            return r.json()

    async def delete_vmcp(self, uuid_or_name: str) -> None:
        headers = {"Accept": "application/json"}
        if self._store.token:
            headers["Authorization"] = f"Bearer {self._store.token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.delete(
                f"{self._store.base_url}/vmcp_servers/{uuid_or_name}",
                headers=headers,
            )
            r.raise_for_status()

    # Tools ------------------------------------------------------------------
    async def create_tool(
        self,
        manifest: Dict[str, Any],
        *,
        module_content: bytes,
        module_filename: str,
    ) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self._store.token:
            headers["Authorization"] = f"Bearer {self._store.token}"
        files = {"module": (module_filename, io.BytesIO(module_content), "text/x-python")}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._store.base_url}/tools/",
                params=_flatten_query(manifest),
                files=files,
                headers=headers,
            )
            r.raise_for_status()
            return r.json()

    async def delete_tool(self, uuid_or_name: str) -> None:
        headers = {"Accept": "application/json"}
        if self._store.token:
            headers["Authorization"] = f"Bearer {self._store.token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.delete(
                f"{self._store.base_url}/tools/{uuid_or_name}",
                headers=headers,
            )
            r.raise_for_status()

    # Skills -----------------------------------------------------------------
    async def create_skill(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self._store.token:
            headers["Authorization"] = f"Bearer {self._store.token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{self._store.base_url}/skills/",
                params=_flatten_query(manifest),
                headers=headers,
            )
            r.raise_for_status()
            return r.json()

    async def delete_skill(self, uuid_or_name: str) -> None:
        headers = {"Accept": "application/json"}
        if self._store.token:
            headers["Authorization"] = f"Bearer {self._store.token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.delete(
                f"{self._store.base_url}/skills/{uuid_or_name}",
                headers=headers,
            )
            r.raise_for_status()


def _flatten_query(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Serialise a manifest dict to a form the SBS Query-schema endpoints accept.

    Nested values (params, extra, tags) are JSON-encoded so they survive
    transport as query parameters.
    """
    import json

    out: Dict[str, Any] = {}
    for k, v in manifest.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v)
        elif v is None:
            continue
        else:
            out[k] = v
    return out
