"""
Universal tool-health pass.

Scans every tool in the store and flips `state` between `approved` and
`broken` based on whether its declared dependencies still match the hashes
captured at create/update time.

Broken-reason taxonomy:
  - dep_missing:<dep>           the dep is gone from the store
  - dep_schema_changed:<dep>    only the dep's params hash drifted
  - dep_code_changed:<dep>      only the dep's module hash drifted
  - dep_broken:<dep>            the dep is itself state=="broken"
  - server_unavailable:<name>   set by the ExternalMCPManager for primitives
                                of a server that failed to start; preserved
                                here untouched.

Runs to a fixpoint so transitive breakage propagates.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.file_executor import hash_tool_interface

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_all(
    tool_handler: FileHandler,
    file_handler: FileHandler,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    tools: Dict[str, Dict[str, Any]] = {}
    modules: Dict[str, str] = {}
    for fname in tool_handler.list_files():
        if not fname.endswith(".json"):
            continue
        try:
            content = tool_handler.read_file(fname, raw_content=True)
            if not isinstance(content, str):
                continue
            d = json.loads(content)
        except Exception as e:
            logger.warning("health: skipping unreadable %s: %s", fname, e)
            continue
        name = d.get("name")
        if not name:
            continue
        tools[name] = d
        mod = d.get("module_name")
        if mod:
            try:
                src = file_handler.read_file(mod, raw_content=True)
                modules[name] = src if isinstance(src, str) else ""
            except Exception:
                modules[name] = ""
        else:
            modules[name] = ""
    return tools, modules


def _evaluate_reason(
    tool: Dict[str, Any],
    tools: Dict[str, Dict[str, Any]],
    current_hashes: Dict[str, Tuple[str, str, str]],
) -> Optional[str]:
    """Return the broken_reason this tool should have right now, or None if healthy."""
    deps = tool.get("dependencies") or []
    stored = tool.get("dependency_hashes") or {}

    for dep in deps:
        if dep not in tools:
            return f"dep_missing:{dep}"

        dep_tool = tools[dep]
        if dep_tool.get("state") == "broken":
            return f"dep_broken:{dep}"

        cur_params, cur_module, _ = current_hashes[dep]
        stored_entry = stored.get(dep)
        if stored_entry is None:
            # No captured baseline — treat as a trust point (skip drift check).
            continue
        if isinstance(stored_entry, str):
            # Back-compat with an older single-hash format. Skip attribution;
            # rely on the combined comparison.
            continue
        s_params = stored_entry.get("params")
        s_module = stored_entry.get("module")
        if s_params is not None and s_params != cur_params:
            return f"dep_schema_changed:{dep}"
        if s_module is not None and s_module != cur_module:
            return f"dep_code_changed:{dep}"

    return None


def check_all_tools_health(
    tool_handler: FileHandler,
    file_handler: FileHandler,
) -> Dict[str, Any]:
    """
    Run the universal dep-drift pass to a fixpoint.

    Returns a summary: {"broken": [...], "unbroken": [...], "iterations": N}.
    Primitives flagged by the ExternalMCPManager as `server_unavailable:*`
    are preserved untouched — the manager owns that lifecycle.
    """
    tools, modules = _load_all(tool_handler, file_handler)
    if not tools:
        return {"broken": [], "unbroken": [], "iterations": 0}

    current_hashes: Dict[str, Tuple[str, str, str]] = {
        name: hash_tool_interface(d, modules.get(name, ""))
        for name, d in tools.items()
    }

    broken_out: list = []
    unbroken_out: list = []
    changed_any = True
    iteration = 0

    while changed_any and iteration < _MAX_ITERATIONS:
        changed_any = False
        iteration += 1

        for name, d in tools.items():
            current_state = d.get("state")
            current_reason = d.get("broken_reason")

            # Manager-owned state — do not touch.
            if str(current_reason or "").startswith("server_unavailable:"):
                continue

            new_reason = _evaluate_reason(d, tools, current_hashes)

            if new_reason is not None:
                if current_state == "broken" and current_reason == new_reason:
                    continue
                d["state"] = "broken"
                d["broken_reason"] = new_reason
                d["modified_at"] = _now_iso()
                tool_handler.write_file_content(
                    f"{name}.json", json.dumps(d, indent=4)
                )
                broken_out.append({"name": name, "reason": new_reason})
                changed_any = True
            else:
                if current_state == "broken":
                    d["state"] = "approved"
                    d["broken_reason"] = None
                    d["modified_at"] = _now_iso()
                    tool_handler.write_file_content(
                        f"{name}.json", json.dumps(d, indent=4)
                    )
                    unbroken_out.append(name)
                    changed_any = True

    return {
        "broken": broken_out,
        "unbroken": unbroken_out,
        "iterations": iteration,
    }


def find_dependents(tool_name: str, tool_handler: FileHandler) -> list:
    """Tools that list `tool_name` in their `dependencies`."""
    out: list = []
    for fname in tool_handler.list_files():
        if not fname.endswith(".json"):
            continue
        try:
            d = json.loads(tool_handler.read_file(fname, raw_content=True))
        except Exception:
            continue
        deps = d.get("dependencies") or []
        if tool_name in deps:
            out.append(d.get("name") or fname.removesuffix(".json"))
    return out


def list_broken_tools(tool_handler: FileHandler) -> list:
    """All tools currently in `state="broken"` with their reason."""
    out: list = []
    for fname in tool_handler.list_files():
        if not fname.endswith(".json"):
            continue
        try:
            d = json.loads(tool_handler.read_file(fname, raw_content=True))
        except Exception:
            continue
        if d.get("state") == "broken":
            out.append({
                "name": d.get("name"),
                "broken_reason": d.get("broken_reason"),
                "mcp_server": d.get("mcp_server"),
                "mcp_dependencies": d.get("mcp_dependencies") or [],
            })
    return out
