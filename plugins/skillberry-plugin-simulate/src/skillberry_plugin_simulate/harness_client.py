"""Async HTTP client for the simulation-harness REST API."""
import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

SIM_PATH = "/api/v1/simulation"


class HarnessError(RuntimeError):
    pass


class HarnessTimeout(HarnessError):
    pass


class HarnessClient:
    """Wraps the harness REST endpoints with transparent 410 session reset."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client
        self._last_spec: Optional[Dict[str, Any]] = None
        self._last_mcp_port: Optional[int] = None

    async def create_simulation(self, openapi_spec: Dict[str, Any], mcp_port: int) -> None:
        self._last_spec = openapi_spec
        self._last_mcp_port = mcp_port
        resp = await self._client.post(
            SIM_PATH, json={"openapi": openapi_spec, "mcp_port": mcp_port}
        )
        if resp.status_code >= 400:
            raise HarnessError(f"create_simulation failed: {resp.status_code} {resp.text}")

    async def _resubmit(self) -> None:
        if self._last_spec is None or self._last_mcp_port is None:
            raise HarnessError("Cannot resubmit: no prior simulation spec recorded")
        logger.warning("Harness session expired (410); resubmitting simulation spec")
        await self.create_simulation(self._last_spec, self._last_mcp_port)

    async def get_status(self) -> Dict[str, Any]:
        resp = await self._client.get(SIM_PATH)
        if resp.status_code == 410:
            await self._resubmit()
            resp = await self._client.get(SIM_PATH)
        if resp.status_code >= 400:
            raise HarnessError(f"get_status failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def wait_until_ready(self, timeout: float = 120.0, interval: float = 2.0) -> str:
        elapsed = 0.0
        while True:
            status = await self.get_status()
            if status.get("status") == "ready":
                mcp_url = status.get("mcp_url")
                if not mcp_url:
                    raise HarnessError("Harness ready but returned no mcp_url")
                return mcp_url
            if elapsed >= timeout:
                raise HarnessTimeout(f"Harness not ready after {timeout}s")
            await asyncio.sleep(interval)
            elapsed += interval

    async def delete_simulation(self) -> None:
        resp = await self._client.delete(SIM_PATH)
        if resp.status_code >= 400 and resp.status_code != 404:
            raise HarnessError(f"delete_simulation failed: {resp.status_code} {resp.text}")
