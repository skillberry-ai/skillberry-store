"""Tests for DAST_SCOPE (cumulative mcp|registered|discovered) gating."""

import copy

import pytest

from skillberry_plugin_dast.engine import scope


def test_default_is_mcp(monkeypatch):
    monkeypatch.delenv("DAST_SCOPE", raising=False)
    assert scope.current_scope() == "mcp"


def test_unknown_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("DAST_SCOPE", "bogus")
    assert scope.current_scope() == "mcp"


def test_cumulative_inclusion():
    # mcp: only mcp
    assert scope.mcp_enabled("mcp")
    assert not scope.registered_enabled("mcp")
    assert not scope.discovered_enabled("mcp")
    # registered: mcp + registered
    assert scope.mcp_enabled("registered")
    assert scope.registered_enabled("registered")
    assert not scope.discovered_enabled("registered")
    # discovered: all
    assert scope.mcp_enabled("discovered")
    assert scope.registered_enabled("discovered")
    assert scope.discovered_enabled("discovered")


# ── scope filters which entry points get exercised directly ───────────────────

from skillberry_plugin_dast.engine.fuzz import (  # noqa: E402
    GENERATOR_NAME,
    generator_available,
)
from skillberry_plugin_dast.plugin import SkillberryPluginDast  # noqa: E402

requires_engine = pytest.mark.skipif(
    not generator_available(),
    reason=f"input generator {GENERATOR_NAME!r} not installed",
)


def _skill_store():
    """Async in-memory store: a skill referencing one tool ("send") whose module
    also has a Tier-2 discovered function ("helper").
    """
    src = "def send(p):\n    return p\ndef helper(q):\n    return q\n"
    objs = {
        ("skill", "sk1"): {
            "uuid": "sk1",
            "name": "demo",
            "tool_uuids": ["t1"],
            "snippet_uuids": [],
        },
        ("tool", "t1"): {
            "uuid": "t1",
            "name": "send",
            "module_name": "s.py",
            "params": {
                "properties": {"p": {"type": "string"}},
                "required": ["p"],
                "optional": [],
            },
        },
    }

    class Store:
        def __init__(self):
            self._o = objs
            self._modules = {("t1", "s.py"): src}

        async def get_skill(self, u):
            return copy.deepcopy(self._o.get(("skill", u)))

        async def get_tool(self, u):
            return copy.deepcopy(self._o.get(("tool", u)))

        async def get_snippet(self, u):
            return None

        async def update_skill(self, u, d):
            self._o[("skill", u)] = copy.deepcopy(d)
            return True

        async def update_tool(self, u, d):
            return True

        async def update_snippet(self, u, d):
            return True

        async def get(self, path, params=None):
            if path.startswith("/tools/") and path.endswith("/module"):
                uuid = path[len("/tools/") : -len("/module")]
                tool = self._o.get(("tool", uuid)) or {}
                module = tool.get("module_name")
                return self._modules.get((uuid, module))
            return None

    return Store()


def _plugin_with(store):
    p = SkillberryPluginDast()
    p._store = store
    return p


def _exercised_names(block):
    return {e["name"] for e in block["entry_points"] if e["exercised"]}


@requires_engine
@pytest.mark.asyncio
async def test_scope_mcp_exercises_no_direct_entry_points(monkeypatch):
    monkeypatch.delenv("DAST_LIVE", raising=False)  # no twin in dry-run
    monkeypatch.setenv("DAST_SCOPE", "mcp")
    p = _plugin_with(_skill_store())
    block = (await p.scan("skill", "sk1"))["dast"]
    # mcp scope: nothing exercised via direct invocation
    assert block["coverage"]["exercised"] == 0
    assert block["scanner"]["scope"] == "mcp"
    # discovery still reports what exists
    assert block["coverage"]["entry_points_total"] >= 2


@requires_engine
@pytest.mark.asyncio
async def test_scope_registered_exercises_only_tier1(monkeypatch):
    monkeypatch.delenv("DAST_LIVE", raising=False)
    monkeypatch.setenv("DAST_SCOPE", "registered")
    p = _plugin_with(_skill_store())
    block = (await p.scan("skill", "sk1"))["dast"]
    names = _exercised_names(block)
    assert "send" in names  # Tier-1 tool
    assert "helper" not in names  # Tier-2 excluded at this scope


@requires_engine
@pytest.mark.asyncio
async def test_scope_discovered_exercises_tier1_and_tier2(monkeypatch):
    monkeypatch.delenv("DAST_LIVE", raising=False)
    monkeypatch.setenv("DAST_SCOPE", "discovered")
    p = _plugin_with(_skill_store())
    block = (await p.scan("skill", "sk1"))["dast"]
    names = _exercised_names(block)
    assert "send" in names and "helper" in names
