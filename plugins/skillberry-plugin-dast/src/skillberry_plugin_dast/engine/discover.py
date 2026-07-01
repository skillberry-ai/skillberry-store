"""Entry-point discovery — Tier 1 (registered tools) + Tier 2 (AST public API).

Pure and store-decoupled: the plugin gathers a skill's tool dicts and module
sources from the store and hands them here. Tier 1 comes from tool metadata
(name + param schema). Tier 2 walks each module's AST for public top-level
functions/classes and ``__main__`` blocks — the surfaces an external component
could import and call directly.

Discovery is STATIC: dynamically-registered/dispatched entry points (Tier 3) are
not guaranteed; the report flags this in its coverage note.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Tuple

from .base import (
    KIND_CLASS,
    KIND_FUNCTION,
    KIND_MAIN,
    KIND_TOOL,
    EntryPoint,
)

# (module_name, source) blob pairs, like the dependency-tracker plugin uses.
Blob = Tuple[str, str]


def _tier1_from_tools(tools: List[Dict[str, Any]]) -> List[EntryPoint]:
    """Tier-1 entry points from registered tool dicts."""
    out: List[EntryPoint] = []
    for tool in tools:
        name = tool.get("name")
        if not name:
            continue
        params = tool.get("params")
        # ToolParamsSchema may arrive as a model-dump dict or already a dict.
        if hasattr(params, "model_dump"):
            params = params.model_dump()
        if not isinstance(params, dict):
            params = {"properties": {}, "required": [], "optional": []}
        out.append(
            EntryPoint(
                name=name,
                kind=KIND_TOOL,
                module=tool.get("module_name") or "",
                params={
                    "properties": params.get("properties") or {},
                    "required": list(params.get("required") or []),
                    "optional": list(params.get("optional") or []),
                },
                tool_uuid=tool.get("uuid"),
            )
        )
    return out


def _is_main_block(node: ast.AST) -> bool:
    """True for ``if __name__ == "__main__":``."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.comparators) != 1:
        return False
    left, right = test.left, test.comparators[0]
    left_is_name = isinstance(left, ast.Name) and left.id == "__name__"
    right_is_main = isinstance(right, ast.Constant) and right.value == "__main__"
    return left_is_name and right_is_main


def _signature(node: ast.AST) -> List[str]:
    """Positional + keyword parameter names of a function/class __init__."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    args = node.args
    names = [a.arg for a in (args.posonlyargs + args.args + args.kwonlyargs)]
    return [n for n in names if n not in ("self", "cls")]


def _tier2_from_module(module: str, source: str) -> List[EntryPoint]:
    """Tier-2 public functions/classes + __main__ from one module's AST."""
    try:
        tree = ast.parse(source or "")
    except (SyntaxError, ValueError):
        return []
    out: List[EntryPoint] = []
    # Only TOP-LEVEL defs (module body), not nested ones.
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            out.append(
                EntryPoint(
                    name=node.name,
                    kind=KIND_FUNCTION,
                    module=module,
                    signature=_signature(node),
                )
            )
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            # use __init__ signature if present for fuzzing the constructor
            init_sig: List[str] = []
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "__init__":
                    init_sig = _signature(sub)
                    break
            out.append(
                EntryPoint(
                    name=node.name,
                    kind=KIND_CLASS,
                    module=module,
                    signature=init_sig,
                )
            )
        elif _is_main_block(node):
            out.append(EntryPoint(name="__main__", kind=KIND_MAIN, module=module))
    return out


def discover_entry_points(
    tools: List[Dict[str, Any]], blobs: List[Blob]
) -> List[EntryPoint]:
    """Discover Tier-1 + Tier-2 entry points; de-dup Tier-2 against Tier-1.

    A tool's own function (Tier-1) shadows the same-named Tier-2 function in its
    module, so we keep the richer Tier-1 entry and drop the duplicate.
    """
    tier1 = _tier1_from_tools(tools)
    tool_names = {ep.name for ep in tier1}

    tier2: List[EntryPoint] = []
    for module, source in blobs:
        for ep in _tier2_from_module(module, source):
            # de-dup: a Tier-2 function matching a registered tool name is the
            # tool's own entry point, already covered by Tier-1.
            if ep.kind == KIND_FUNCTION and ep.name in tool_names:
                continue
            tier2.append(ep)

    # Stable order: tools first, then Tier-2 by (module, name).
    tier2.sort(key=lambda e: (e.module, e.name))
    return tier1 + tier2
