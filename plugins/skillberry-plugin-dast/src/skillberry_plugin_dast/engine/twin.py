"""Benign vMCP twin — a faithful, observed stand-in for the real MCP server.

Wraps the store's ``VirtualMcpServer`` so a skill under test calls *this* instead
of the production tool server. The twin is assumed **benign**: it executes the
skill's own tools faithfully and simply **records** every call (args + result) so
the runner can attribute MCP activity to the entry point that triggered it.

The server is constructed standalone: manifests and execution come from an
injected ``tool_source`` (see :mod:`.tool_source`), no transport is started
(``serve=False`` — the twin is driven in-process, nothing dials into it), calls
are observed through the server's own ``on_invoke`` hook, and metrics are off so
a per-scan server name cannot leak Prometheus label cardinality.

Import of the store module is lazy + guarded so the engine stays unit-testable
without the full store (tests inject a fake twin).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BenignMcpTwin:
    """Lifecycle + call-log wrapper around a VirtualMcpServer for given tools."""

    def __init__(
        self,
        name: str,
        tool_uuids: List[str],
        tool_source: Optional[Any] = None,
        env_id: str = "",
    ):
        self.name = name
        self.tool_uuids = list(tool_uuids or [])
        self.tool_source = tool_source
        self.env_id = env_id
        self._server = None
        self.calls: List[Dict[str, Any]] = []  # observed MCP calls

    def start(self) -> "BenignMcpTwin":
        """Stand up the underlying VirtualMcpServer in observed, transport-less mode."""
        from skillberry_store.standalone import VirtualMcpServer

        self._server = VirtualMcpServer(
            name=self.name,
            description="DAST benign MCP twin",
            port=None,
            tools=self.tool_uuids,
            env_id=self.env_id,
            tool_source=self.tool_source,
            # Driven in-process via drive_tool; nothing connects to the twin, so
            # it takes no port and starts no server thread.
            serve=False,
            # A per-scan server name would otherwise leak label cardinality.
            metrics_enabled=False,
            on_invoke=self._record,
        )
        return self

    def _record(self, record: Any) -> None:
        """Record one observed invocation — successes and failures alike.

        Failures matter most here: a tool that raises under adversarial input is
        exactly what the scan is looking for.
        """
        try:
            entry: Dict[str, Any] = {
                "tool": record.tool_name,
                "args": record.parameters,
                "result_excerpt": str(record.result)[:300],
            }
            if record.failed:
                entry["error"] = str(record.error)
            self.calls.append(entry)
        except Exception:
            pass

    def tool_names(self) -> List[str]:
        """Names of the tools this twin serves (as registered on the server)."""
        if self._server is None:
            return []
        return self._server.tool_names()

    async def drive_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Invoke one tool *through the MCP server's dispatch* (Scope A).

        Goes via the server's ``invoke_tool`` — the same path a real MCP client
        call resolves to — so the call is faithfully executed and recorded by the
        ``on_invoke`` hook. Raises if the server isn't started.
        """
        if self._server is None:
            raise RuntimeError("twin not started")
        return await self._server.invoke_tool(tool_name, parameters, self.env_id)

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.stop()
            except Exception as e:
                logger.debug("dast twin stop failed: %s", e)
            self._server = None
