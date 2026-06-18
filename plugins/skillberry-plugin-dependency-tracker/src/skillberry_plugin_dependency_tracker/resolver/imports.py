"""Extract top-level external imports from Python source via AST.

Mirrors the AST precedent in the store
(``src/skillberry_store/modules/file_executor.py`` uses ``ast.Import`` /
``ast.ImportFrom``) but reduces each import to its **top-level module name** and
filters out the standard library and relative imports, leaving only the external
modules whose distributions we then resolve.

Best-effort: a ``SyntaxError`` (e.g. Python 2 code, a template fragment) yields an
empty set rather than raising — a scan should never fail on unparseable input.
"""

from __future__ import annotations

import ast
import sys
from typing import Set

# Python 3.10+ (the plugin's floor) exposes the stdlib module set directly.
_STDLIB: Set[str] = set(getattr(sys, "stdlib_module_names", ()))

# Small belt-and-suspenders fallback for names that are effectively stdlib/builtin
# but may not appear in stdlib_module_names on every interpreter.
_EXTRA_STDLIB = {
    "__future__",
    "builtins",
    "typing_extensions",  # ships with CPython tooling; treat as non-external noise
}


def _is_stdlib(top_level: str) -> bool:
    return top_level in _STDLIB or top_level in _EXTRA_STDLIB


def extract_top_level_imports(code: str) -> Set[str]:
    """Return the set of external top-level module names imported by ``code``.

    - ``import a.b.c`` / ``import a as x`` -> ``a``
    - ``from a.b import c`` -> ``a`` (only absolute imports; ``node.level == 0``)
    - relative imports (``from . import x``, ``from ..p import y``) are skipped
    - standard-library top-level names are excluded
    - unparseable input returns an empty set
    """
    try:
        tree = ast.parse(code or "")
    except (SyntaxError, ValueError):
        return set()

    found: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = (alias.name or "").split(".")[0]
                if top and not _is_stdlib(top):
                    found.add(top)
        elif isinstance(node, ast.ImportFrom):
            # node.level > 0 means a relative import (no external dist).
            if node.level and node.level > 0:
                continue
            module = node.module or ""
            top = module.split(".")[0]
            if top and not _is_stdlib(top):
                found.add(top)
    return found
