"""HTTP client for the SBS REST API used by plugins."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class StoreClient:
    """Thin HTTP wrapper over the SBS REST surface used by plugins.

    Plugins call ``StoreClient(base_url, token)`` (or ``get_store_client()`` for env-based
    construction) and then use the object methods, which map to REST endpoints.
    """

    def __init__(self, base_url: str, token: Optional[str] = None, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json,
                headers=self._headers(),
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            if not r.content:
                return None
            try:
                return r.json()
            except ValueError:
                return r.text

    # Skills
    async def get_skill(self, uuid: str) -> Optional[Dict[str, Any]]:
        return await self._request("GET", f"/skills/{uuid}")

    async def list_skills(self) -> List[Dict[str, Any]]:
        result = await self._request("GET", "/skills/")
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("skills", []) or list(result.values())
        return result  # type: ignore[return-value]

    async def update_skill(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/skills/{uuid}", json=data)

    async def patch_skill(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", f"/skills/{uuid}", json=data)

    async def update_skill_tags(self, uuid: str, tags: List[str]) -> Optional[Dict[str, Any]]:
        skill = await self.get_skill(uuid)
        if skill is None:
            return None
        existing = set(skill.get("tags") or [])
        skill["tags"] = list(existing.union(tags))
        return await self.update_skill(uuid, skill)

    # Tools
    async def get_tool(self, uuid: str) -> Optional[Dict[str, Any]]:
        return await self._request("GET", f"/tools/{uuid}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        result = await self._request("GET", "/tools/")
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("tools", []) or list(result.values())
        return result  # type: ignore[return-value]

    async def update_tool(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/tools/{uuid}", json=data)

    async def patch_tool(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", f"/tools/{uuid}", json=data)

    async def update_tool_tags(self, uuid: str, tags: List[str]) -> Optional[Dict[str, Any]]:
        tool = await self.get_tool(uuid)
        if tool is None:
            return None
        existing = set(tool.get("tags") or [])
        tool["tags"] = list(existing.union(tags))
        return await self.update_tool(uuid, tool)

    # Snippets
    async def get_snippet(self, uuid: str) -> Optional[Dict[str, Any]]:
        return await self._request("GET", f"/snippets/{uuid}")

    async def list_snippets(self) -> List[Dict[str, Any]]:
        result = await self._request("GET", "/snippets/")
        if result is None:
            return []
        if isinstance(result, dict):
            return result.get("snippets", []) or list(result.values())
        return result  # type: ignore[return-value]

    async def update_snippet(self, uuid: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PUT", f"/snippets/{uuid}", json=data)

    # Generic
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Optional[Any] = None) -> Any:
        return await self._request("POST", path, json=json)


def get_store_client() -> StoreClient:
    """Construct a StoreClient from SKILLBERRY_STORE_URL / SKILLBERRY_STORE_TOKEN env vars."""
    url = os.environ.get("SKILLBERRY_STORE_URL", "http://127.0.0.1:8000")
    token = os.environ.get("SKILLBERRY_STORE_TOKEN") or None
    return StoreClient(url, token=token)
