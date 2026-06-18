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

    async def create_simulation(
        self,
        openapi_spec: Dict[str, Any],
        mcp_port: int,
        *,
        startup_retries: int = 10,
        startup_delay: float = 2.0,
    ) -> None:
        """POST the simulation spec, retrying on connection errors to handle harness startup lag."""
        self._last_spec = openapi_spec
        self._last_mcp_port = mcp_port
        for attempt in range(startup_retries + 1):
            try:
                resp = await self._client.post(
                    SIM_PATH, json={"openapi_spec": openapi_spec, "mcp_port": mcp_port}
                )
                break
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as exc:
                if attempt == startup_retries:
                    raise HarnessError(
                        f"create_simulation: harness not reachable after "
                        f"{startup_retries} retries: {exc}"
                    ) from exc
                logger.debug(
                    "Harness not yet reachable (attempt %d/%d): %s – retrying in %.1fs",
                    attempt + 1, startup_retries, exc, startup_delay,
                )
                await asyncio.sleep(startup_delay)
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

    async def wait_until_ready(self, timeout: float = 600.0, interval: float = 2.0) -> str:
        elapsed = 0.0
        while True:
            status = await self.get_status()
            sim_status = status.get("status")
            if sim_status == "ready":
                mcp_url = status.get("mcp_url")
                if not mcp_url:
                    raise HarnessError("Harness ready but returned no mcp_url")
                return mcp_url
            if sim_status == "failed":
                error = status.get("error") or "unknown error"
                raise HarnessError(f"Harness simulation failed: {error}")
            if elapsed >= timeout:
                raise HarnessTimeout(f"Harness not ready after {timeout}s")
            await asyncio.sleep(interval)
            elapsed += interval

    async def delete_simulation(self) -> None:
        resp = await self._client.delete(SIM_PATH)
        if resp.status_code >= 400 and resp.status_code != 404:
            raise HarnessError(f"delete_simulation failed: {resp.status_code} {resp.text}")
