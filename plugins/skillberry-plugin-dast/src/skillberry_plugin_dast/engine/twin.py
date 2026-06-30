"""Benign vMCP twin — a faithful, observed stand-in for the real MCP server.

Wraps the store's ``VirtualMcpServer`` so a skill under test calls *this* instead
of the production tool server. The twin is assumed **benign**: it executes the
skill's own tools faithfully and simply **records** every call (args + result) so
the runner can attribute MCP activity to the entry point that triggered it.

Import of the store module is lazy + guarded so the engine stays unit-testable
without the full store (tests inject a fake twin).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BenignMcpTwin:
    """Lifecycle + call-log wrapper around a VirtualMcpServer for given tools."""

    def __init__(self, name: str, tool_uuids: List[str], env_id: str = ""):
        self.name = name
        self.tool_uuids = list(tool_uuids or [])
        self.env_id = env_id
        self._server = None
        self.calls: List[Dict[str, Any]] = []  # observed MCP calls
        self.port: Optional[int] = None

    def start(self) -> "BenignMcpTwin":
        """Stand up the underlying VirtualMcpServer and wrap invoke_tool to log."""
        from skillberry_store.modules.vmcp_server import VirtualMcpServer

        self._server = VirtualMcpServer(
            name=self.name,
            description="DAST benign MCP twin",
            port=None,  # auto-pick from VMCP_SERVERS_START_PORT
            tools=self.tool_uuids,
            env_id=self.env_id,
        )
        self.port = getattr(self._server, "port", None)
        self._wrap_invoke()
        return self

    def _wrap_invoke(self) -> None:
        """Wrap the server's invoke_tool to record args + result (observe-only)."""
        server = self._server
        orig = server.invoke_tool

        async def _logged(tool_name, parameters, env_id):  # faithful + observed
            result = await orig(tool_name, parameters, env_id)
            try:
                self.calls.append(
                    {
                        "tool": tool_name,
                        "args": parameters,
                        "result_excerpt": str(result)[:300],
                    }
                )
            except Exception:
                pass
            return result

        server.invoke_tool = _logged  # type: ignore[method-assign]

    def tool_names(self) -> List[str]:
        """Names of the tools this twin serves (as registered on the server)."""
        if self._server is None:
            return []
        manifests = getattr(self._server, "_tool_manifests", None)
        if isinstance(manifests, dict) and manifests:
            return list(manifests.keys())
        return []

    async def drive_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Invoke one tool *through the MCP server's dispatch* (Scope A).

        Goes via the server's ``invoke_tool`` — the same path a real MCP client
        call resolves to — so the call is faithfully executed and recorded by the
        ``_logged`` wrapper. Raises if the server isn't started.
        """
        if self._server is None:
            raise RuntimeError("twin not started")
        return await self._server.invoke_tool(tool_name, parameters, self.env_id)

    def url(self) -> Optional[str]:
        """SSE URL the skill's MCP client should target (host side)."""
        return f"http://127.0.0.1:{self.port}/sse" if self.port else None

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.stop()
            except Exception as e:
                logger.debug("dast twin stop failed: %s", e)
            self._server = None


def host_address_for_container() -> str:
    """The address a container uses to reach a server on the host.

    Docker Desktop (macOS/Windows) resolves ``host.docker.internal``; on Linux
    the default bridge gateway is ``172.17.0.1``. Best-effort heuristic.
    """
    import platform

    return "172.17.0.1" if platform.system() == "Linux" else "host.docker.internal"
