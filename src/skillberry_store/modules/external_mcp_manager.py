"""
External MCP server import — manager, transports, reconciliation.

Maintains one long-lived `ClientSession` per imported external MCP server
(stdio / sse / streamable-http), reconciles exposed tools into the store as
`packaging_format="mcp"` primitives, and proxies tool calls over the pooled
session.

The legacy single-tool MCP path (tools with `packaging_format="mcp"` +
`mcp_url` but no `mcp_server`) is NOT routed here — it stays on the existing
transient-SSE path in `file_executor.py` for back-compat.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
import urllib.request
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.tools.configure import get_external_mcps_directory

logger = logging.getLogger(__name__)

_VALID_TRANSPORTS = ("stdio", "sse", "http")

# Module-level reference to the active manager. Set during FastAPI startup by
# server.py so FileExecutor can reach it without threading a dependency through
# every constructor.
_current_manager: Optional["ExternalMCPManager"] = None


def set_current_manager(manager: Optional["ExternalMCPManager"]) -> None:
    global _current_manager
    _current_manager = manager


def get_current_manager() -> Optional["ExternalMCPManager"]:
    return _current_manager


# ---------------------------------------------------------------------------
# Input normalization — accepts five wire shapes, returns list[entry].
# ---------------------------------------------------------------------------

def _default_fetch_url(url: str) -> Any:
    """Default URL fetcher for the `source_url` input shape."""
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


def normalize_mcp_input(
    data: Any,
    fetch_url: Optional[Callable[[str], Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Collapse any of the supported config shapes into a normalized list of
    server entries.

    Accepted shapes:
      (1) {"mcpServers": {name: entry, ...}}
      (2) {name: entry, ...}                        # bare dict
      (3) [entry_with_name, ...]                    # list form
      (4) {"name": "...", "type"|"transport": ...}  # single entry
      (5) {"source_url": "https://..."}             # fetch + recurse
    """
    fetch_url = fetch_url or _default_fetch_url

    if isinstance(data, dict) and set(data.keys()) == {"source_url"}:
        fetched = fetch_url(data["source_url"])
        return normalize_mcp_input(fetched, fetch_url=fetch_url)

    if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
        return [_normalize_entry(name, entry) for name, entry in data["mcpServers"].items()]

    if isinstance(data, list):
        out: List[Dict[str, Any]] = []
        for entry in data:
            if not isinstance(entry, dict) or "name" not in entry:
                raise ValueError("list-form entries must each have a 'name' field")
            out.append(_normalize_entry(entry["name"], entry))
        return out

    if isinstance(data, dict):
        if "name" in data and any(k in data for k in ("type", "transport", "command", "url")):
            return [_normalize_entry(data["name"], data)]
        if data and all(isinstance(v, dict) for v in data.values()):
            return [_normalize_entry(name, entry) for name, entry in data.items()]

    raise ValueError("unrecognized mcp-servers input shape")


def _normalize_entry(name: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    # External MCP names become primitive prefixes (`<name>__<tool>`) and
    # are used as URL segments in /external-mcps/{name}; enforce the same
    # Anthropic slug format we require for skills and VMCPs.
    from skillberry_store.schemas.name_validation import (
        is_valid_store_name,
        format_hint,
        STORE_NAME_PATTERN,
    )
    if not is_valid_store_name(name):
        raise ValueError(
            f"entry {name!r}: invalid MCP server name. "
            f"{format_hint('External MCP')} (pattern: {STORE_NAME_PATTERN})"
        )

    transport = raw.get("transport") or raw.get("type")
    if transport is None:
        if raw.get("command"):
            transport = "stdio"
        elif raw.get("url"):
            transport = "sse"
        else:
            raise ValueError(f"entry '{name}': cannot infer transport")

    if transport not in _VALID_TRANSPORTS:
        raise ValueError(f"entry '{name}': unknown transport '{transport}'")

    entry: Dict[str, Any] = {
        "name": name,
        "transport": transport,
        "command": raw.get("command"),
        "args": list(raw.get("args") or []),
        "env": dict(raw.get("env") or {}),
        "url": raw.get("url"),
        "headers": dict(raw.get("headers") or {}),
        "enabled": bool(raw.get("enabled", True)),
    }

    if transport == "stdio":
        if not entry["command"]:
            raise ValueError(f"entry '{name}': stdio transport requires 'command'")
    else:
        if not entry["url"]:
            raise ValueError(f"entry '{name}': {transport} transport requires 'url'")
    return entry


# ---------------------------------------------------------------------------
# Helpers — params conversion, manifest building, secret redaction.
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def params_from_input_schema(schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert an MCP tool's JSON-Schema inputSchema into the store's params
    shape (`ToolParamsSchema`).
    """
    if not schema:
        return {"type": "object", "properties": {}, "required": [], "optional": []}
    properties = schema.get("properties") or {}
    required = list(schema.get("required") or [])
    return {
        "type": schema.get("type", "object"),
        "properties": properties,
        "required": required,
        "optional": [k for k in properties.keys() if k not in required],
    }


def build_primitive_manifest(
    prefixed_name: str,
    server_name: str,
    remote_description: str,
    remote_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Create a fresh manifest for a tool imported from an external MCP server.

    Primitives have `mcp_server` set (the source they were imported from) but
    an empty `mcp_dependencies` list — the latter is reserved for composites
    that aggregate dependencies across their children. When the health pass
    and `compute_mcp_dependencies` walk a primitive, they always pull in the
    `mcp_server` value, so no information is lost.
    """
    now = _now_iso()
    return {
        "name": prefixed_name,
        "uuid": str(uuid.uuid4()),
        "version": "1.0.0",
        "description": remote_description or "",
        "state": "approved",
        "tags": [f"mcp:{server_name}"],
        "extra": {},
        "created_at": now,
        "modified_at": now,
        "module_name": None,
        "programming_language": "python",
        "packaging_format": "mcp",
        "params": remote_params,
        "returns": None,
        "dependencies": None,
        "mcp_url": None,
        "mcp_server": server_name,
        "mcp_dependencies": [],
        "dependency_hashes": {},
        "broken_reason": None,
        "bundled_with_mcps": True,
    }


_SECRET_HEADER_HINTS = ("key", "token", "auth", "secret", "password", "bearer")


def redact_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of entry with header values and env values masked."""
    masked = dict(entry)
    masked["headers"] = {k: _mask(v) for k, v in (entry.get("headers") or {}).items()}
    masked["env"] = {k: _mask(v) for k, v in (entry.get("env") or {}).items()}
    return masked


def _mask(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "•••"
    return value[:2] + "•" * max(4, len(value) - 4) + value[-2:]


# ---------------------------------------------------------------------------
# _ServerRunner — holds one session inside a long-lived task.
# ---------------------------------------------------------------------------

class _ServerRunner:
    """
    Owns the session for a single server.

    A background task enters the transport + ClientSession context managers
    and then awaits a shutdown event. All MCP calls run from arbitrary caller
    tasks against `self.session`; the runner only coordinates lifecycle.
    """

    def __init__(self, entry: Dict[str, Any]):
        self.entry = entry
        self.name = entry["name"]
        self.session: Optional[ClientSession] = None
        self.status: str = "stopped"
        self.last_error: Optional[str] = None
        self._ready = asyncio.Event()
        self._shutdown = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._call_lock = asyncio.Lock()

    async def start(self, startup_timeout: float = 30.0) -> None:
        self._ready.clear()
        self._shutdown.clear()
        self.last_error = None
        self.status = "starting"
        self._task = asyncio.create_task(self._run(), name=f"ext-mcp-{self.name}")
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=startup_timeout)
        except asyncio.TimeoutError:
            self.status = "error"
            self.last_error = f"startup timeout after {startup_timeout}s"
            self._shutdown.set()
            raise RuntimeError(self.last_error)
        if self.status == "error":
            raise RuntimeError(f"failed to start {self.name}: {self.last_error}")

    async def stop(self, stop_timeout: float = 10.0) -> None:
        self._shutdown.set()
        task = self._task
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=stop_timeout)
            except asyncio.TimeoutError:
                logger.warning("External MCP %s did not stop within %.1fs; cancelling", self.name, stop_timeout)
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self._task = None
        self.session = None
        if self.status != "error":
            self.status = "stopped"

    async def _run(self) -> None:
        try:
            t = self.entry["transport"]
            if t == "stdio":
                params = StdioServerParameters(
                    command=self.entry["command"],
                    args=list(self.entry.get("args") or []),
                    env=self.entry.get("env") or None,
                )
                async with stdio_client(params) as (read, write):
                    await self._run_session(read, write)
            elif t == "sse":
                async with sse_client(
                    self.entry["url"],
                    headers=self.entry.get("headers") or None,
                ) as (read, write):
                    await self._run_session(read, write)
            elif t == "http":
                async with streamablehttp_client(
                    self.entry["url"],
                    headers=self.entry.get("headers") or None,
                ) as (read, write, _):
                    await self._run_session(read, write)
            else:
                raise ValueError(f"unknown transport: {t}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.status = "error"
            self.last_error = str(e)
            self._ready.set()
            logger.error("External MCP %s failed: %s", self.name, e, exc_info=True)

    async def _run_session(self, read, write) -> None:
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=15.0)
            self.session = session
            self.status = "running"
            self._ready.set()
            try:
                await self._shutdown.wait()
            finally:
                self.session = None

    async def list_remote_tools(self) -> List[Any]:
        if self.status != "running" or self.session is None:
            raise RuntimeError(f"server {self.name} is not running (status={self.status})")
        result = await asyncio.wait_for(self.session.list_tools(), timeout=15.0)
        return list(result.tools or [])

    async def call_tool(
        self,
        remote_tool_name: str,
        args: Optional[Dict[str, Any]],
        timeout: float = 30.0,
    ) -> str:
        if self.status != "running" or self.session is None:
            raise RuntimeError(f"server {self.name} is not running (status={self.status})")
        async with self._call_lock:
            result = await asyncio.wait_for(
                self.session.call_tool(remote_tool_name, arguments=args or {}),
                timeout=timeout,
            )
        content = result.content or []
        if not content:
            return ""
        first = content[0]
        return getattr(first, "text", str(first))


# ---------------------------------------------------------------------------
# ExternalMCPManager — orchestration layer.
# ---------------------------------------------------------------------------

class ExternalMCPManager:
    """
    Lifecycle and call-site for every imported external MCP server.

    Stored on `app.state.external_mcp_manager`; constructed with the tool and
    module FileHandlers so it can write primitive manifests directly.
    """

    def __init__(
        self,
        tool_handler: FileHandler,
        file_handler: FileHandler,
        config_handler: Optional[FileHandler] = None,
    ):
        self._tool_handler = tool_handler
        self._file_handler = file_handler
        self._config_handler = config_handler or FileHandler(get_external_mcps_directory())
        self._runners: Dict[str, _ServerRunner] = {}
        self._lock = asyncio.Lock()

    # ----- Lifecycle ---------------------------------------------------------

    async def start_all(self) -> None:
        for fname in self._config_handler.list_files():
            if not fname.endswith(".json"):
                continue
            try:
                entry = self._read_config(fname)
            except Exception as e:
                logger.error("Failed to read external MCP config %s: %s", fname, e)
                continue
            if not entry or not entry.get("enabled", True):
                continue
            try:
                await self.start(entry, persist=False)
            except Exception as e:
                logger.error("Failed to auto-start external MCP %s: %s", entry.get("name"), e)
        # Boot-time drift sweep — any composite whose dep changed while the
        # store was offline gets flagged now. Also unbreaks things that
        # now match again.
        self._run_health_pass()

    async def stop_all(self) -> None:
        async with self._lock:
            names = list(self._runners.keys())
            for name in names:
                try:
                    await self._runners[name].stop()
                except Exception as e:
                    logger.warning("Error stopping external MCP %s: %s", name, e)
            self._runners.clear()

    async def start(self, entry: Dict[str, Any], persist: bool = True) -> Dict[str, Any]:
        """Start or restart a server; reconcile its primitives on success."""
        name = entry["name"]
        async with self._lock:
            if name in self._runners:
                try:
                    await self._runners[name].stop()
                except Exception:
                    pass
                self._runners.pop(name, None)

            if persist:
                self._write_config(entry)

            runner = _ServerRunner(entry)
            self._runners[name] = runner

            try:
                await runner.start()
            except Exception as e:
                logger.error("External MCP %s failed to start: %s", name, e)
                # Primitives from this server → broken, server_unavailable.
                self._mark_primitives_unavailable(name)
                return {"name": name, "status": "error", "error": str(e)}

            reconcile_summary = await self._reconcile(name)
            # Any primitive add/update/remove may have flipped composites'
            # drift state — run the universal health pass so we surface it.
            health = self._run_health_pass()
            return {
                "name": name,
                "status": "running",
                "reconcile": reconcile_summary,
                "health": health,
            }

    async def stop(self, name: str, remove: bool = False) -> None:
        async with self._lock:
            runner = self._runners.pop(name, None)
            if runner:
                await runner.stop()
            if remove:
                fname = f"{name}.json"
                if fname in self._config_handler.list_files():
                    self._config_handler.delete_file(fname)

    async def restart(self, name: str) -> Dict[str, Any]:
        entry = self._read_config(f"{name}.json")
        if entry is None:
            raise ValueError(f"unknown external MCP: {name}")
        return await self.start(entry, persist=False)

    async def remove(self, name: str) -> Dict[str, Any]:
        """Stop, delete config, delete primitives. Composites → `state=broken`."""
        await self.stop(name, remove=True)
        removed_primitives = self._delete_primitives(name)
        health = self._run_health_pass()
        return {
            "name": name,
            "removed_primitives": removed_primitives,
            "health": health,
        }

    # ----- Read-only inspection ---------------------------------------------

    def list_servers(self) -> List[Dict[str, Any]]:
        servers: List[Dict[str, Any]] = []
        for fname in self._config_handler.list_files():
            if not fname.endswith(".json"):
                continue
            try:
                entry = self._read_config(fname)
            except Exception:
                continue
            if entry is None:
                continue
            name = entry["name"]
            runner = self._runners.get(name)
            status = runner.status if runner else "stopped"
            last_error = runner.last_error if runner else None
            servers.append({
                "name": name,
                "transport": entry["transport"],
                "enabled": entry.get("enabled", True),
                "status": status,
                "last_error": last_error,
                "tool_count": self._count_primitives(name),
                "config": redact_entry(entry),
            })
        return servers

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        for s in self.list_servers():
            if s["name"] == name:
                return s
        return None

    async def list_remote_tools(self, name: str) -> List[Dict[str, Any]]:
        runner = self._runners.get(name)
        if not runner:
            raise ValueError(f"unknown external MCP: {name}")
        remote = await runner.list_remote_tools()
        return [
            {
                "name": t.name,
                "description": getattr(t, "description", "") or "",
                "inputSchema": getattr(t, "inputSchema", None) or {},
            }
            for t in remote
        ]

    async def call_tool(
        self,
        server_name: str,
        remote_tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> str:
        runner = self._runners.get(server_name)
        if not runner:
            raise RuntimeError(f"unknown external MCP: {server_name}")
        return await runner.call_tool(remote_tool_name, args, timeout=timeout)

    def find_dependents(self, server_name: str) -> List[str]:
        """Tools that will transition to `state="broken"` if this server is removed.

        Excludes primitives of the server itself — those are cascade-deleted
        alongside the server, not flagged broken.
        """
        out: List[str] = []
        for fname in self._tool_handler.list_files():
            if not fname.endswith(".json"):
                continue
            try:
                d = json.loads(self._tool_handler.read_file(fname, raw_content=True))
            except Exception:
                continue
            # A server's own primitives go away with it — don't list them.
            if d.get("mcp_server") == server_name:
                continue
            deps = d.get("mcp_dependencies") or []
            if server_name in deps:
                out.append(d.get("name") or fname.removesuffix(".json"))
        return out

    # ----- Reconciliation ----------------------------------------------------

    async def _reconcile(self, name: str) -> Dict[str, Any]:
        """
        Diff remote tools against stored primitives for `name`:
         - new upstream → create primitive manifest
         - changed schema → update params + description in place
         - removed upstream → delete primitive manifest (+ associated module file)
        """
        runner = self._runners.get(name)
        if runner is None or runner.status != "running":
            self._mark_primitives_unavailable(name)
            return {"status": "server_unavailable"}

        try:
            remote = await runner.list_remote_tools()
        except Exception as e:
            logger.error("list_tools failed for %s: %s", name, e)
            self._mark_primitives_unavailable(name)
            return {"status": "list_tools_failed", "error": str(e)}

        remote_by_prefixed: Dict[str, Any] = {}
        for t in remote:
            prefixed = f"{name}__{t.name}"
            remote_by_prefixed[prefixed] = t

        stored = self._load_primitives(name)

        added: List[str] = []
        updated: List[str] = []
        removed: List[str] = []

        for prefixed, remote_tool in remote_by_prefixed.items():
            params = params_from_input_schema(getattr(remote_tool, "inputSchema", None))
            description = getattr(remote_tool, "description", "") or ""
            if prefixed not in stored:
                manifest = build_primitive_manifest(
                    prefixed_name=prefixed,
                    server_name=name,
                    remote_description=description,
                    remote_params=params,
                )
                self._tool_handler.write_file_content(
                    f"{prefixed}.json", json.dumps(manifest, indent=4)
                )
                added.append(prefixed)
            else:
                existing = stored[prefixed]
                changed = (
                    existing.get("params") != params
                    or (existing.get("description") or "") != description
                )
                was_unavailable = str(existing.get("broken_reason") or "").startswith(
                    "server_unavailable:"
                )
                if changed or was_unavailable:
                    existing["params"] = params
                    existing["description"] = description
                    existing["modified_at"] = _now_iso()
                    if was_unavailable:
                        existing["state"] = "approved"
                        existing["broken_reason"] = None
                    self._tool_handler.write_file_content(
                        f"{prefixed}.json", json.dumps(existing, indent=4)
                    )
                    updated.append(prefixed)

        for prefixed in set(stored) - set(remote_by_prefixed):
            try:
                self._tool_handler.delete_file(f"{prefixed}.json")
                removed.append(prefixed)
            except Exception as e:
                logger.warning("Failed to delete stale primitive %s: %s", prefixed, e)

        return {"added": added, "updated": updated, "removed": removed}

    # ----- Primitive bookkeeping --------------------------------------------

    def _load_primitives(self, server_name: str) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for fname in self._tool_handler.list_files():
            if not fname.endswith(".json"):
                continue
            try:
                d = json.loads(self._tool_handler.read_file(fname, raw_content=True))
            except Exception:
                continue
            if d.get("mcp_server") == server_name:
                out[d["name"]] = d
        return out

    def _count_primitives(self, server_name: str) -> int:
        return len(self._load_primitives(server_name))

    def _mark_primitives_unavailable(self, server_name: str) -> None:
        reason = f"server_unavailable:{server_name}"
        for prefixed, d in self._load_primitives(server_name).items():
            if d.get("broken_reason") == reason and d.get("state") == "broken":
                continue
            d["state"] = "broken"
            d["broken_reason"] = reason
            d["modified_at"] = _now_iso()
            self._tool_handler.write_file_content(
                f"{prefixed}.json", json.dumps(d, indent=4)
            )

    def _delete_primitives(self, server_name: str) -> List[str]:
        removed: List[str] = []
        for prefixed in list(self._load_primitives(server_name).keys()):
            try:
                self._tool_handler.delete_file(f"{prefixed}.json")
                removed.append(prefixed)
            except Exception as e:
                logger.warning("Failed to delete primitive %s: %s", prefixed, e)
        return removed

    # ----- Health pass integration ------------------------------------------

    def _run_health_pass(self) -> Dict[str, Any]:
        """Run the universal tool health pass; swallow failures."""
        try:
            # Local import avoids a circular reference at module-load time.
            from skillberry_store.modules.tool_health import check_all_tools_health
            return check_all_tools_health(self._tool_handler, self._file_handler)
        except Exception as e:  # noqa: BLE001
            logger.warning("health pass after external MCP mutation failed: %s", e)
            return {"broken": [], "unbroken": [], "iterations": 0, "error": str(e)}

    # ----- Config file I/O ---------------------------------------------------

    def _read_config(self, filename: str) -> Optional[Dict[str, Any]]:
        try:
            content = self._config_handler.read_file(filename, raw_content=True)
        except Exception:
            return None
        if not isinstance(content, str):
            return None
        try:
            return json.loads(content)
        except Exception:
            return None

    def _write_config(self, entry: Dict[str, Any]) -> None:
        name = entry["name"]
        now = _now_iso()
        payload = dict(entry)
        payload.setdefault("created_at", now)
        payload["modified_at"] = now
        payload.setdefault("status", "stopped")
        payload.setdefault("last_error", None)
        self._config_handler.write_file_content(
            f"{name}.json", json.dumps(payload, indent=4)
        )
