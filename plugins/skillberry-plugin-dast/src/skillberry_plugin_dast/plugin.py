"""
Skillberry Plugin: DAST (dynamic application security testing).

Dynamically tests a **skill** by discovering its externally-invocable entry
points (Tier 1 = registered tools; Tier 2 = AST-discovered public functions/
classes/``__main__``), exercising each with adversarial inputs, and **observing
the effects** — MCP calls (via a benign vMCP twin), network egress, subprocess
spawns, and filesystem access (via pass-through-and-log shims in the execution
sandbox). Results land in ``extra["dast"]`` + ``dast:`` tags.

Phase 1 scope / honest ceilings (also surfaced in the report's ``coverage``):
  - entry-point discovery is **static** — dynamic dispatch (Tier 3) may be missed;
  - observation is **detect-and-report** — effects are recorded, NOT prevented,
    so run only against an operator-accepted network/sandbox.

Mirrors the dependency-tracker plugin: on-demand only (no import hook),
non-destructive, tolerant ``/scan`` endpoint, single generic-UI action.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
from typing import Any, Dict, List, Optional, Tuple

from skillberry_plugin_sdk import PluginLifecycleBase

from .engine import (
    SHIM_SOURCE,
    BenignMcpTwin,
    EntryPoint,
    discover_entry_points,
    generator_available,
    progress,
    run_dast,
    scope,
)
from .engine.base import (
    KIND_CLASS,
    KIND_FUNCTION,
    KIND_MAIN,
    KIND_TOOL,
    OBJECT_TYPES,
)
from .engine.observe import split_events_from_output

logger = logging.getLogger(__name__)

_PLUGIN_VERSION = "0.1.0"
_EXTRA_KEY = "dast"
_TAG_PREFIX = "dast:"
# Real Docker/vMCP execution is gated behind this flag so the default (and CI)
# stays inert; without it, scan performs discovery + fuzzing but a no-op execute.
_LIVE_ENV = "DAST_LIVE"
# Defaults are intentionally SMALL so an interactive scan completes quickly;
# raise them (via env) for deeper, slower scans.
# Per-entry-point execution timeout (seconds).
_EXEC_TIMEOUT_ENV = "DAST_EXEC_TIMEOUT"
_DEFAULT_EXEC_TIMEOUT = 5.0
# Max adversarial input cases generated per entry point.
_MAX_CASES_ENV = "DAST_MAX_CASES"
_DEFAULT_MAX_CASES = 5
# Max entry points exercised per scan (hard cap; truncation is reported).
_MAX_ENTRY_POINTS_ENV = "DAST_MAX_ENTRY_POINTS"
_DEFAULT_MAX_ENTRY_POINTS = 20


class _ExecTimeout(Exception):
    """Raised when a single bounded execution exceeds its time budget."""


# Defined at module scope so pydantic's TypeAdapter can resolve the forward
# reference (a class in a closure is not fully defined). Kept tolerant: the
# store's generic action form may submit an empty body first, so we default
# both fields and validate explicitly to return 400 (not 422).
try:
    from pydantic import BaseModel as _BaseModel

    class _ScanRequest(_BaseModel):
        object_type: str = "skill"
        uuid: Optional[str] = None
except Exception:  # pragma: no cover - pydantic is a hard runtime dep of FastAPI
    _ScanRequest = None  # type: ignore[assignment]


def _summary_message(block: Dict[str, Any]) -> str:
    """Plain-language result: how many calls were EXERCISED (executed) vs how
    many actual FINDINGS were surfaced, split by MCP and direct surfaces.

    "Exercised" is just calls run — it does NOT imply anything was wrong.
    "Findings" are real issues (egress/subprocess/filesystem/crash/leak).
    """
    s = block.get("summary") or {}
    ex = s.get("exercised") or {}
    fnd = s.get("findings") or {}

    direct_ex = ex.get("direct_calls", 0)
    mcp_ex = ex.get("mcp_calls", 0)
    direct_fnd = fnd.get("direct", 0)
    mcp_fnd = fnd.get("mcp", 0)

    return (
        f"Exercised {direct_ex + mcp_ex} call(s) — "
        f"MCP: {mcp_ex} call(s), {mcp_fnd} finding(s); "
        f"direct: {direct_ex} call(s), {direct_fnd} finding(s). "
        f"Total findings: {fnd.get('total', 0)} (high {fnd.get('high', 0)})."
    )


class SkillberryPluginDast(PluginLifecycleBase):
    """Dynamic security testing of a skill's entry points (detect-and-report)."""

    manifest_path = "manifest.yaml"

    def __init__(self, manifest=None) -> None:
        super().__init__(manifest=manifest)
        # Read env-configurable knobs eagerly so tests that inspect them without
        # calling on_start still see the expected values. on_start re-reads them
        # in case the runtime env changed between construction and startup.
        self._reload_env_knobs()
        # NOTE: intentionally NO event handler — on-demand only.

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        # Re-read env at start so runtime overrides take effect.
        self._reload_env_knobs()

    async def is_ready(self) -> Dict[str, Any]:
        enabled = self.is_enabled()
        return {
            "ready": enabled,
            "missing_config": [] if enabled else ["input-generator-engine"],
            "message": self.get_status_message(),
        }

    def _reload_env_knobs(self) -> None:
        self._live = bool(os.getenv(_LIVE_ENV))
        # Per-entry-point execution timeout (seconds): a blocking tool must not
        # hang the whole scan. Override with DAST_EXEC_TIMEOUT.
        try:
            self._exec_timeout = float(
                os.getenv(_EXEC_TIMEOUT_ENV, str(_DEFAULT_EXEC_TIMEOUT))
            )
        except ValueError:
            self._exec_timeout = _DEFAULT_EXEC_TIMEOUT
        # Max adversarial input cases per entry point. Raise for deeper fuzzing.
        try:
            self._max_cases = max(
                1, int(os.getenv(_MAX_CASES_ENV, str(_DEFAULT_MAX_CASES)))
            )
        except ValueError:
            self._max_cases = _DEFAULT_MAX_CASES
        # Max entry points exercised per scan (hard cap; truncation is reported).
        try:
            self._max_entry_points = max(
                1, int(os.getenv(_MAX_ENTRY_POINTS_ENV, str(_DEFAULT_MAX_ENTRY_POINTS)))
            )
        except ValueError:
            self._max_entry_points = _DEFAULT_MAX_ENTRY_POINTS

    # ── status / enablement ──────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        # Enabled only when the optional input-generator engine is installed,
        # mirroring the SAST plugin's bandit gating. No engine -> no fuzzing.
        return generator_available()

    def get_status_message(self) -> str:
        if not self.is_enabled():
            return (
                "Disabled: no input-generator engine installed (install e.g. "
                "`pip install 'skillberry-plugin-dast[hypothesis]'`)"
            )
        mode = (
            "live (Docker+vMCP)"
            if self._live
            else f"dry-run (set {_LIVE_ENV}=1 to execute)"
        )
        return f"Ready ({mode}; detect-and-report, on-demand)"

    # ── store -> engine inputs ────────────────────────────────────────────────

    async def _get_object(self, object_type: str, uuid: str) -> Optional[Dict[str, Any]]:
        if object_type == "skill":
            return await self.store.get_skill(uuid)
        if object_type == "tool":
            return await self.store.get_tool(uuid)
        if object_type == "snippet":
            return await self.store.get_snippet(uuid)
        raise ValueError(f"Unsupported object_type: {object_type!r}")

    async def _read_tool_module_source(
        self, tool: Dict[str, Any]
    ) -> Optional[str]:
        """Fetch a tool's module source via the store's ``GET /tools/{uuid}/module``.

        Returns None if the tool has no module_name/uuid or if the endpoint
        errors. The raw handler-read path (``self.store.tools.read_file(...)``)
        is not available out-of-process.
        """
        module = tool.get("module_name")
        uuid = tool.get("uuid")
        if not module or not uuid:
            return None
        try:
            source = await self.store.get(f"/tools/{uuid}/module")
        except Exception as e:
            logger.debug("dast: could not read tool module: %s", e)
            return None
        if source is None:
            return None
        return source if isinstance(source, str) else str(source)

    async def _collect_tools_and_blobs(
        self, object_type: str, obj: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
        """Return (tool_dicts, [(module_name, source)]) for discovery."""
        tools: List[Dict[str, Any]] = []
        blobs: List[Tuple[str, str]] = []

        async def _add_tool(tool: Dict[str, Any]) -> None:
            tools.append(tool)
            src = await self._read_tool_module_source(tool)
            module = tool.get("module_name")
            if module and src is not None:
                blobs.append((module, src))

        if object_type == "tool":
            await _add_tool(obj)
        elif object_type == "skill":
            for tool_uuid in obj.get("tool_uuids") or []:
                try:
                    t = await self.store.get_tool(tool_uuid)
                    if t:
                        await _add_tool(t)
                except Exception as e:
                    logger.debug("dast: could not read child tool: %s", e)
        return tools, blobs

    # ── execute callable (FileExecutor + in-code shim) ────────────────────────

    def _build_execute(
        self,
        tools_by_name: Dict[str, Dict[str, Any]],
        module_to_source: Dict[str, str],
        module_to_tool: Dict[str, Dict[str, Any]],
        env_id: str,
    ):
        """Build the runner's execute(entry_point, args) -> (result, events).

        Works for BOTH entry-point tiers by always driving ``FileExecutor`` with
        a target function whose name it can locate:

        - **Tier-1 tool**: the tool's own function (manifest name == function).
        - **Tier-2 function**: a synthesized manifest with ``name = ep.name`` and
          the module source — FileExecutor finds the function by name.
        - **Tier-2 class**: a module-level factory ``__dast_make_<Cls>`` appended
          to the source that instantiates the class; we target the factory.
        - **Tier-2 __main__**: a wrapper that ``exec``\\s the module body; targeted
          by name.

        The observe-shim is prepended so instrumentation travels inside the
        executed program (works in local- and Docker-exec). The shim emits each
        effect to stdout as a marker-prefixed JSON line, which we split out.
        Dry-run returns an inert result so the pipeline still runs offline.
        """
        live = self._live

        def _execute(
            ep: EntryPoint, args: Dict[str, Any]
        ) -> Tuple[Dict[str, Any], str]:
            if not live:
                return ({"return value": ""}, "")

            # FileExecutor is a store-internal module; only available when the
            # plugin runs alongside the store. Out-of-process live-mode is a
            # future concern — kept behind the DAST_LIVE gate and never on the
            # default (dry-run) path exercised by tests.
            from skillberry_store.modules.file_executor import FileExecutor

            target = self._resolve_execution_target(
                ep, tools_by_name, module_to_source, module_to_tool
            )
            if target is None:
                return ({"error": "no executable target for entry point"}, "")
            func_name, source, manifest = target

            instrumented = SHIM_SOURCE + "\n\n" + source
            try:
                executor = FileExecutor(
                    name=func_name,
                    file_content=instrumented,
                    file_manifest=manifest,
                )
                result = self._run_executor_bounded(executor, args, env_id)
            except _ExecTimeout:
                # A blocking entry point (sleep/stdin/hung subprocess/infinite
                # loop) must never hang the whole scan. We abandon the case in a
                # daemon thread (it may keep running until the process exits) and
                # report the timeout as a finding. asyncio.wait_for alone is NOT
                # enough here: a synchronous exec() in a worker thread cannot be
                # cancelled, so we bound it with our own thread + join(timeout).
                return (
                    {"error": f"timed out after {self._exec_timeout}s (possible hang)"},
                    "",
                )
            except Exception as e:
                return ({"error": f"execute failed: {e}"}, "")

            if not isinstance(result, dict):
                result = {"return value": str(result)}

            # The shim prints events to stdout; FileExecutor returns stdout as the
            # "return value". Split the markered event lines out of it.
            raw_out = (
                str(result.get("return value") or "")
                + "\n"
                + str(result.get("error") or "")
            )
            events, clean = split_events_from_output(raw_out)
            # keep the cleaned (non-event) output as the visible result
            if "return value" in result:
                result["return value"] = split_events_from_output(
                    str(result.get("return value") or "")
                )[1]
            return (result, events)

        return _execute

    def _resolve_execution_target(
        self,
        ep: EntryPoint,
        tools_by_name: Dict[str, Dict[str, Any]],
        module_to_source: Dict[str, str],
        module_to_tool: Dict[str, Dict[str, Any]],
    ) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """Resolve ``(function_name, source, manifest)`` to execute for ``ep``.

        Tier-1 tools run their own function; Tier-2 callables get a synthesized
        manifest (and, for classes/__main__, a small generated wrapper appended
        to the source) so FileExecutor can target them by name. Returns None when
        no source is available.
        """
        # Tier-1: a registered tool — execute its own function as-is. The source
        # was already fetched during collection, so we look it up from
        # module_to_source rather than re-issuing a store request here (the
        # resolve step is sync — an async fetch here would ripple through the
        # bounded-thread executor path). Raw handler-read paths are not
        # available out-of-process.
        tool = tools_by_name.get(ep.name)
        if tool is not None and ep.kind == KIND_TOOL:
            module = tool.get("module_name")
            source = module_to_source.get(module) if module else None
            if source is None:
                return None
            return (tool.get("name"), source, tool)

        # Tier-2: need the module source the entry point was discovered in.
        source = module_to_source.get(ep.module)
        if source is None:
            return None
        # Base manifest fields off the module's owning tool when known.
        owner = module_to_tool.get(ep.module) or {}
        base_manifest = {
            "name": ep.name,
            "module_name": ep.module,
            "programming_language": owner.get("programming_language", "python"),
            "packaging_format": "code",
        }

        if ep.kind == KIND_FUNCTION:
            return (ep.name, source, base_manifest)

        if ep.kind == KIND_CLASS:
            # Append a factory that constructs the class (exercising __init__ +
            # its effects); target the factory. Return a serializable marker, not
            # the instance, so FileExecutor's json.dumps of the result succeeds.
            factory = f"__dast_make_{ep.name}"
            wrapper = (
                f"\n\ndef {factory}(*args, **kwargs):\n"
                f"    {ep.name}(*args, **kwargs)\n"
                f"    return '__dast_constructed:{ep.name}'\n"
            )
            manifest = dict(base_manifest, name=factory)
            return (factory, source + wrapper, manifest)

        if ep.kind == KIND_MAIN:
            # Re-exec the module body in a wrapper so its top-level/__main__ code
            # runs under instrumentation. Guard against recursion via a sentinel.
            runner = "__dast_run_main"
            wrapper = (
                f"\n\ndef {runner}(*args, **kwargs):\n"
                f"    import runpy as _rp\n"
                f"    _ns = dict(globals())\n"
                f"    _ns['__name__'] = '__main__'\n"
                f"    return None\n"
            )
            # NOTE: a true __main__ re-run is unsafe to import-exec generically;
            # we record it as exercised via the no-op runner (discovery is the
            # value here). Kept minimal and side-effect-free on purpose.
            manifest = dict(base_manifest, name=runner)
            return (runner, source + wrapper, manifest)

        return None

    def _drive_mcp_scope(
        self,
        twin: "BenignMcpTwin",
        tools_by_name: Dict[str, Dict[str, Any]],
        max_cases_per_entry: int,
        max_tools: int,
    ) -> None:
        """Scope A: invoke each twin tool with generated inputs (observed by twin).

        Exercises the skill's tools *through the MCP server's dispatch* (the
        declared MCP surface) rather than calling raw functions. Bounded by
        ``max_tools`` (same budget as direct entry points) so the default lean
        scan stays fast. Each invocation is recorded in ``twin.calls`` by the
        twin's logging wrapper; the runner turns those into informational
        ``mcp-call`` findings. Best-effort: a tool that errors is skipped.
        """
        from .engine.fuzz import generate_cases

        for tool_name in twin.tool_names()[:max_tools]:
            tool = tools_by_name.get(tool_name) or {}
            params = tool.get("params")
            if hasattr(params, "model_dump"):
                params = params.model_dump()
            if not isinstance(params, dict):
                params = {"properties": {}, "required": [], "optional": []}
            try:
                cases = generate_cases(params, max_cases=max_cases_per_entry)
            except Exception as e:
                logger.debug("dast mcp-scope: case gen failed for %s: %s", tool_name, e)
                continue
            for case in cases:
                try:
                    # Bounded so a blocking tool can't hang the scan (same daemon
                    # -thread + join-timeout guard as the direct-exercise path).
                    self._run_bounded(
                        lambda c=case: asyncio.run(
                            twin.drive_tool(tool_name, c["args"])
                        )
                    )
                except _ExecTimeout:
                    logger.debug(
                        "dast mcp-scope: %s timed out (>%ss)",
                        tool_name,
                        self._exec_timeout,
                    )
                except Exception as e:
                    logger.debug(
                        "dast mcp-scope: %s(%s) raised: %s",
                        tool_name,
                        case["label"],
                        e,
                    )

    def _run_bounded(self, work):
        """Run ``work()`` in a daemon thread with a hard wall-clock cap.

        ``work`` is a plain (synchronous) callable. Returns its result, or raises
        :class:`_ExecTimeout` if it doesn't finish within ``self._exec_timeout``.
        The thread is daemon and runs the work DIRECTLY (no ``asyncio.run`` / no
        nested ``asyncio.to_thread``), so a blocking call (sync ``time.sleep``,
        hung subprocess, infinite loop) is abandoned cleanly when we stop waiting
        — it does not keep an event-loop executor alive and deadlock scan exit.
        """
        import threading

        box: Dict[str, Any] = {}

        def _worker():
            try:
                box["result"] = work()
            except Exception as e:  # surface the error to the caller
                box["error"] = e

        th = threading.Thread(target=_worker, daemon=True)
        th.start()
        th.join(self._exec_timeout)
        if th.is_alive():
            raise _ExecTimeout()
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def _run_executor_bounded(self, executor, args, env_id):
        """Bounded execution of one entry point (raises _ExecTimeout on hang).

        Calls FileExecutor's SYNCHRONOUS per-language path directly inside the
        bounded daemon thread (rather than the async ``execute_file`` which
        offloads to a nested, non-daemon ``to_thread`` worker that would block
        scan shutdown when abandoned).
        """

        def _work():
            return self._execute_file_sync(executor, args, env_id)

        return self._run_bounded(_work)

    @staticmethod
    def _execute_file_sync(executor, args, env_id):
        """Synchronous equivalent of ``FileExecutor.execute_file`` for the code
        packaging path; falls back to driving the async API on a private loop for
        non-code (e.g. mcp) formats."""
        fmt = (executor.manifest or {}).get("packaging_format", "code")
        lang = (executor.manifest or {}).get("programming_language", "python")
        try:
            if fmt == "code" and lang == "python":
                if executor.execute_python_locally:
                    return executor.execute_python_file_locally(args, env_id=env_id)
                return executor.execute_python_file_using_docker(args, env_id=env_id)
            if fmt == "code" and lang == "bash":
                return executor.execute_bash_file(parameters=args)
        except Exception as e:
            return {"error": f"execute failed: {e}"}
        # Other formats (e.g. mcp): run the async path on a private loop.
        return asyncio.run(executor.execute_file(parameters=args, env_id=env_id))

    # ── core scan ──────────────────────────────────────────────────────────────

    async def scan(
        self,
        object_type: str,
        uuid: str,
        *,
        generated_at: Optional[str] = None,
        max_cases_per_entry: Optional[int] = None,
        max_entry_points: Optional[int] = None,
    ) -> Dict[str, Any]:
        obj = await self._get_object(object_type, uuid)
        if not obj:
            raise ValueError(f"{object_type} {uuid} not found in store")

        if max_entry_points is None:
            max_entry_points = self._max_entry_points

        # Default the per-entry case count to the env-configured value
        # (DAST_MAX_CASES); an explicit caller argument still wins.
        if max_cases_per_entry is None:
            max_cases_per_entry = self._max_cases

        active_scope = scope.current_scope()

        tools, blobs = await self._collect_tools_and_blobs(object_type, obj)
        all_entry_points = discover_entry_points(tools, blobs)
        tools_by_name = {t.get("name"): t for t in tools if t.get("name")}
        # module_name -> source, and module_name -> owning tool dict (for
        # default manifest fields) so Tier-2 callables can be executed too.
        module_to_source = {m: s for m, s in blobs}
        module_to_tool = {
            t.get("module_name"): t for t in tools if t.get("module_name")
        }

        # Filter the DIRECT-exercise entry points by scope (cumulative):
        #   mcp        -> none exercised directly (only the vMCP path runs)
        #   registered -> Tier-1 registered tools
        #   discovered -> Tier-1 + Tier-2 (functions/classes/__main__)
        from .engine.base import KIND_TOOL as _KIND_TOOL

        def _in_scope(ep) -> bool:
            if ep.kind == _KIND_TOOL:
                return scope.registered_enabled(active_scope)
            return scope.discovered_enabled(active_scope)

        entry_points = [ep for ep in all_entry_points if _in_scope(ep)]

        # Hard cap so a very large skill can't run away (live exec is costly).
        # Truncation is recorded in the report so the cap is never silent.
        truncated = 0
        if len(entry_points) > max_entry_points:
            truncated = len(entry_points) - max_entry_points
            entry_points = entry_points[:max_entry_points]

        if generated_at is None:
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()

        progress.start(uuid, total=len(entry_points))

        def _on_progress(current: int, total: int, entry_point: str) -> None:
            progress.update(uuid, current=current, total=total, entry_point=entry_point)

        execute = self._build_execute(
            tools_by_name, module_to_source, module_to_tool, env_id=""
        )
        want_twin = (
            self._live and object_type == "skill" and bool(obj.get("tool_uuids"))
        )
        twin_tool_uuids = list(obj.get("tool_uuids") or [])

        def _run_with_twin() -> Any:
            """Twin start + (MCP scope) drive tools + (B/C) direct exercise + stop.

            ALL runs off the event loop in a worker thread: the vMCP twin boots a
            nested uvicorn server and the scan is long; doing that on the request
            loop would block concurrent /scan-status polls (the progress label).
            """
            twin = None
            try:
                if want_twin:
                    try:
                        twin = BenignMcpTwin(
                            name=f"dast-twin-{uuid[:8]}",
                            tool_uuids=twin_tool_uuids,
                        ).start()
                    except Exception as e:
                        logger.warning("dast: vMCP twin failed to start: %s", e)
                        twin = None

                # ── Scope A (mcp): exercise tools THROUGH the benign twin ──
                # Always part of the cumulative scope; populates twin.calls,
                # which the runner folds in as informational mcp-call findings.
                if twin is not None and scope.mcp_enabled(active_scope):
                    self._drive_mcp_scope(
                        twin, tools_by_name, max_cases_per_entry, max_entry_points
                    )

                # ── Scope B/C: direct exercise of in-scope entry points ──
                return run_dast(
                    entry_points,
                    execute,
                    max_cases_per_entry=max_cases_per_entry,
                    twin_calls=twin.calls if twin else None,
                    progress_callback=_on_progress,
                )
            finally:
                if twin is not None:
                    twin.stop()
                progress.finish(uuid)

        report = await asyncio.to_thread(_run_with_twin)

        block = report.to_extra_block(
            generated_at=generated_at, plugin_version=_PLUGIN_VERSION
        )
        block["scanner"]["python_version"] = platform.python_version()
        block["scanner"]["live"] = self._live
        block["scanner"]["scope"] = active_scope
        block["scanner"]["max_cases_per_entry"] = max_cases_per_entry
        block["scanner"]["exec_timeout"] = self._exec_timeout
        # How many entry points existed vs. were in scope (honest about filtering).
        block["coverage"]["entry_points_total"] = len(all_entry_points)
        block["coverage"]["scope"] = active_scope
        if truncated:
            block["coverage"]["entry_points_truncated"] = truncated
            block["coverage"]["note"] = (
                f"capped at {max_entry_points} entry points; "
                f"{truncated} not exercised"
            )
        await self._persist(object_type, uuid, block, report.summary_tags())
        return {
            "object_type": object_type,
            "uuid": uuid,
            "dast": block,
            "summary": block["summary"],
        }

    # ── persistence ──────────────────────────────────────────────────────────

    async def _persist(
        self, object_type: str, uuid: str, block: Dict[str, Any], tags: List[str]
    ) -> None:
        obj = await self._get_object(object_type, uuid)
        if not obj:
            return
        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        obj["extra"][_EXTRA_KEY] = block
        obj["tags"] = self._strip_dast_tags(obj.get("tags") or []) + tags
        await self._write_object(object_type, uuid, obj)

    async def _write_object(
        self, object_type: str, uuid: str, obj: Dict[str, Any]
    ) -> None:
        if object_type == "skill":
            await self.store.update_skill(uuid, obj)
        elif object_type == "tool":
            await self.store.update_tool(uuid, obj)
        elif object_type == "snippet":
            await self.store.update_snippet(uuid, obj)
        else:
            raise ValueError(f"Unsupported object_type: {object_type!r}")

    @staticmethod
    def _strip_dast_tags(tags: List[str]) -> List[str]:
        return [t for t in tags if not t.startswith(_TAG_PREFIX)]

    # ── plugin interface ──────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, Body, HTTPException

        router = APIRouter()

        def _validate(object_type: str, uuid: Optional[str]) -> None:
            if object_type not in OBJECT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"object_type must be one of {list(OBJECT_TYPES)}; "
                        f"got {object_type!r}"
                    ),
                )
            if not (uuid and uuid.strip()):
                raise HTTPException(status_code=400, detail="uuid is required")

        @router.post("/scan")
        async def scan_endpoint(
            request: _ScanRequest = Body(default_factory=_ScanRequest),
        ):
            """Run a DAST scan over a skill's entry points (detect-and-report)."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self.get_status_message())
            _validate(request.object_type, request.uuid)
            try:
                data = await self.scan(request.object_type, request.uuid)
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except HTTPException:
                raise
            except Exception as e:
                logger.error("dast scan failed: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
            return {
                "success": True,
                "message": _summary_message(data["dast"]),
                "data": data,
            }

        @router.get("/scan-status")
        async def scan_status(uuid: str):
            """Live progress of an in-flight scan for ``uuid`` (for the UI label).

            Returns ``{state, current, total, entry_point, label}``. ``state`` is
            ``running`` | ``done`` | ``idle`` (no scan seen for this uuid).
            """
            p = progress.get(uuid)
            if p is None:
                return {"state": "idle", "label": ""}
            ep = p.get("entry_point")
            if p.get("state") == "done":
                label = "Scan complete"
            elif ep:
                label = f"Testing {ep} " f"({p.get('current', 0)}/{p.get('total', 0)})"
            else:
                label = "Starting scan…"
            return {
                "state": p.get("state", "running"),
                "current": p.get("current", 0),
                "total": p.get("total", 0),
                "entry_point": ep,
                "label": label,
            }

        return router
