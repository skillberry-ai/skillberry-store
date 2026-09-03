"""Async HTTP client for the simulation-harness REST API.

Contract verified against github.com/skillberry-ai/simulation-harness v0.1.2.
"""
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
    """Wraps the harness REST endpoints.

    Session expiry is NOT handled here: the harness raises SessionExpiredError
    only inside its own tool execution path, where it resets the session itself
    and fails just that one call (core/simulation_instance.py). It never surfaces
    on the status endpoint, and tool calls reach the harness directly from the
    vMCP, so this client never observes it.
    """

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def create_simulation(
        self,
        openapi_spec: Dict[str, Any],
        mcp_port: int,
        *,
        name: Optional[str] = None,
        startup_retries: int = 10,
        startup_delay: float = 2.0,
    ) -> None:
        """POST the simulation spec, retrying on connection errors to handle harness startup lag.

        Returns as soon as the harness accepts the request (202); creation then
        runs in the background — poll `wait_until_ready`.
        """
        payload: Dict[str, Any] = {"openapi_spec": openapi_spec, "mcp_port": mcp_port}
        if name:
            payload["name"] = name
        for attempt in range(startup_retries + 1):
            try:
                resp = await self._client.post(SIM_PATH, json=payload)
                break
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadError,
                # Docker publishes the port before uvicorn binds inside the
                # container; the proxy accepts the connection then closes it
                # without a response ("Server disconnected..."). This is startup
                # lag, not a hard failure, so retry it like the others.
                httpx.RemoteProtocolError,
            ) as exc:
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
        if resp.status_code == 409:
            raise HarnessError(
                f"create_simulation rejected (409): the harness already has an active "
                f"simulation, or MCP port {mcp_port} is already bound inside the "
                f"container (a leaked harness container may still hold it). "
                f"Harness said: {resp.text}"
            )
        if resp.status_code == 422:
            raise HarnessError(
                f"create_simulation rejected (422): the harness would not accept the "
                f"synthesized OpenAPI spec. Harness said: {resp.text}"
            )
        if resp.status_code >= 400:
            raise HarnessError(f"create_simulation failed: {resp.status_code} {resp.text}")

    async def get_status(self) -> Dict[str, Any]:
        resp = await self._client.get(SIM_PATH)
        if resp.status_code == 404:
            raise HarnessError(
                "get_status: the harness has no active simulation — it was deleted "
                "or the harness restarted mid-creation"
            )
        if resp.status_code >= 400:
            raise HarnessError(f"get_status failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def wait_until_ready(self, timeout: float = 600.0, interval: float = 2.0) -> str:
        """Poll until status is `ready`, returning the harness's mcp_url.

        Transitional statuses (`pending`, `generating_skill`, `initializing`) are
        just "not yet"; only `ready` and `failed` are terminal here.
        """
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
                raise HarnessError(f"Harness simulation failed: {_format_error(status)}")
            if elapsed >= timeout:
                raise HarnessTimeout(
                    f"Harness not ready after {timeout}s (last status: {sim_status}"
                    f"{_format_phase(status)})"
                )
            await asyncio.sleep(interval)
            elapsed += interval

    async def delete_simulation(self) -> None:
        resp = await self._client.delete(SIM_PATH)
        if resp.status_code >= 400 and resp.status_code != 404:
            raise HarnessError(f"delete_simulation failed: {resp.status_code} {resp.text}")


def _format_error(status: Dict[str, Any]) -> str:
    """Render the harness's error payload, which is an object as of v0.1.x."""
    error = status.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("code") or "unknown error"
        code = error.get("code")
        return f"{message} ({code})" if code and code != message else str(message)
    return str(error) if error else "unknown error"


def _format_phase(status: Dict[str, Any]) -> str:
    phase = (status.get("progress") or {}).get("phase")
    return f", phase: {phase}" if phase else ""
