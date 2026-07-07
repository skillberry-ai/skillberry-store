"""Proves the input-generator engine is pluggable (a non-Hypothesis engine works).

This is the real flexibility check: register a second, fake engine, select it via
DAST_GENERATOR, and confirm the registry resolves it, the plugin enables on it,
and a scan is driven by it — with no Hypothesis involved.
"""

import copy

import pytest

from skillberry_plugin_dast.engine import generators as gens
from skillberry_plugin_dast.engine.generators.base import InputGenerator


class FakeGenerator(InputGenerator):
    """A trivial, always-available, Hypothesis-free engine."""

    name = "fake"

    def is_available(self) -> bool:
        return True

    def generate_cases(self, params, *, seed=1729, max_cases=24):
        props = params.get("properties") or {}
        if not props:
            return [{"label": "no-args", "args": {}}]
        # one deterministic sentinel value per parameter
        args = {name: f"<fake:{name}>" for name in props}
        return [{"label": "fake-case", "args": args}][:max_cases]


@pytest.fixture
def fake_engine(monkeypatch):
    """Register FakeGenerator and select it via DAST_GENERATOR."""
    reg = dict(gens.GENERATOR_REGISTRY)
    reg["fake"] = FakeGenerator
    monkeypatch.setattr(gens, "GENERATOR_REGISTRY", reg)
    monkeypatch.setenv("DAST_GENERATOR", "fake")
    return FakeGenerator


def test_registry_resolves_selected_engine(fake_engine):
    eng = gens.resolve_generator()
    assert isinstance(eng, FakeGenerator)
    assert gens.any_generator_available() is True
    assert "fake" in gens.status_message()


def test_unknown_selection_is_disabled_with_message(monkeypatch):
    monkeypatch.setenv("DAST_GENERATOR", "does-not-exist")
    assert gens.resolve_generator() is None
    assert "not a registered generator" in gens.status_message()


def test_fuzz_facade_uses_selected_engine(fake_engine):
    # fuzz.generate_cases must delegate to the selected (fake) engine.
    from skillberry_plugin_dast.engine import fuzz

    cases = fuzz.generate_cases(
        {"properties": {"p": {"type": "string"}}, "required": ["p"]}
    )
    assert cases == [{"label": "fake-case", "args": {"p": "<fake:p>"}}]


@pytest.mark.asyncio
async def test_scan_driven_by_fake_engine(fake_engine, monkeypatch):
    """End-to-end: a scan runs powered by the fake engine (no Hypothesis)."""
    from skillberry_plugin_dast.plugin import SkillberryPluginDast

    class Store:
        def __init__(self):
            self._o = {
                ("tool", "t1"): {
                    "uuid": "t1",
                    "name": "send",
                    "module_name": "s.py",
                    "params": {
                        "properties": {"p": {"type": "string"}},
                        "required": ["p"],
                        "optional": [],
                    },
                }
            }
            self._modules = {("t1", "s.py"): "def send(p):\n    return p\n"}

        async def get_tool(self, u):
            return copy.deepcopy(self._o.get(("tool", u)))

        async def get_skill(self, u):
            return None

        async def get_snippet(self, u):
            return None

        async def update_tool(self, u, d):
            self._o[("tool", u)] = copy.deepcopy(d)
            return True

        async def update_skill(self, u, d):
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

    monkeypatch.setenv("DAST_SCOPE", "registered")  # exercise the Tier-1 tool
    p = SkillberryPluginDast()
    p._store = Store()
    assert p.is_enabled() is True  # enabled via the fake engine
    block = (await p.scan("tool", "t1"))["dast"]
    assert (
        block["coverage"]["exercised"] == block["coverage"]["entry_points_discovered"]
    )
    assert block["coverage"]["entry_points_discovered"] >= 1
