"""DAST scope levels — cumulative, env-selectable breadth of what gets exercised.

From leanest/safest to broadest:

  - ``mcp``        — exercise only the skill's tools **via the benign vMCP twin**
                     (the declared MCP surface; nothing runs the raw functions
                     directly).
  - ``registered`` — the above **plus** Tier-1 registered tools exercised directly
                     via FileExecutor.
  - ``discovered`` — the above **plus** Tier-2 AST-discovered functions/classes/
                     __main__ exercised directly.

Cumulative: ``registered`` includes ``mcp``; ``discovered`` includes both.
Selected by the ``DAST_SCOPE`` env var; default is the leanest (``mcp``).
"""

from __future__ import annotations

import os

SCOPE_MCP = "mcp"
SCOPE_REGISTERED = "registered"
SCOPE_DISCOVERED = "discovered"

# Ordered lean -> broad; index encodes inclusion.
_ORDER = [SCOPE_MCP, SCOPE_REGISTERED, SCOPE_DISCOVERED]
_DEFAULT = SCOPE_MCP
_ENV = "DAST_SCOPE"


def current_scope() -> str:
    """Resolve the active scope from ``DAST_SCOPE`` (default ``mcp``).

    Unknown values fall back to the default rather than failing a scan.
    """
    val = (os.getenv(_ENV) or "").strip().lower()
    return val if val in _ORDER else _DEFAULT


def _level(scope: str) -> int:
    return _ORDER.index(scope) if scope in _ORDER else _ORDER.index(_DEFAULT)


def includes(scope: str, layer: str) -> bool:
    """True if ``scope`` (cumulative) includes ``layer``."""
    return _level(scope) >= _level(layer)


def mcp_enabled(scope: str) -> bool:
    return includes(scope, SCOPE_MCP)


def registered_enabled(scope: str) -> bool:
    return includes(scope, SCOPE_REGISTERED)


def discovered_enabled(scope: str) -> bool:
    return includes(scope, SCOPE_DISCOVERED)
