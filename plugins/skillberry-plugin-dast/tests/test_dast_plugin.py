"""Tests for the DAST plugin (mock async store, dry-run; no real Docker/vMCP)."""

import copy

import pytest

from skillberry_plugin_dast.engine.fuzz import GENERATOR_NAME, generator_available
from skillberry_plugin_dast.plugin import SkillberryPluginDast

# Scans that actually exercise params need the optional generator engine.
requires_engine = pytest.mark.skipif(
    not generator_available(),
    reason=f"input generator {GENERATOR_NAME!r} not installed",
)


class FakeAsyncStore:
    """Async in-memory store mirroring the SDK's StoreClient surface.

    Provides ``get_skill``/``get_tool``/``get_snippet``, ``update_*``, and a
    generic ``get(path)`` that resolves ``/tools/{uuid}/module`` to module
    source (matching the store's REST endpoint the SDK uses).
    """

    def __init__(self, objects=None, modules=None):
        self._objs = objects or {}
        # (uuid, filename) -> source
        self._modules = modules or {}

    async def get_skill(self, uuid):
        return copy.deepcopy(self._objs.get(("skill", uuid)))

    async def get_tool(self, uuid):
        return copy.deepcopy(self._objs.get(("tool", uuid)))

    async def get_snippet(self, uuid):
        return copy.deepcopy(self._objs.get(("snippet", uuid)))

    async def update_skill(self, uuid, data):
        self._objs[("skill", uuid)] = copy.deepcopy(data)
        return True

    async def update_tool(self, uuid, data):
        self._objs[("tool", uuid)] = copy.deepcopy(data)
        return True

    async def update_snippet(self, uuid, data):
        self._objs[("snippet", uuid)] = copy.deepcopy(data)
        return True

    async def get(self, path, params=None):
        # /tools/{uuid}/module -> source
        prefix, suffix = "/tools/", "/module"
        if path.startswith(prefix) and path.endswith(suffix):
            uuid = path[len(prefix) : -len(suffix)]
            tool = self._objs.get(("tool", uuid)) or {}
            module = tool.get("module_name")
            return self._modules.get((uuid, module))
        return None


def _plugin(store, monkeypatch):
    monkeypatch.delenv("DAST_LIVE", raising=False)  # dry-run: inert executor
    p = SkillberryPluginDast()
    p._store = store
    return p


# ── manifest / enablement ─────────────────────────────────────────────────────


def test_manifest_slug():
    assert SkillberryPluginDast().manifest.slug == "dast"


def test_manifest_type_evaluator():
    assert SkillberryPluginDast().manifest.plugin_type == "evaluator"


def test_manifest_version():
    assert SkillberryPluginDast().manifest.version == "0.1.0"


def test_manifest_has_api():
    assert SkillberryPluginDast().manifest.has_api is True


def test_enablement_tracks_generator_availability():
    p = SkillberryPluginDast()
    # Enablement tracks the optional engine's availability.
    assert p.is_enabled() == generator_available()


def test_disabled_when_engine_missing(monkeypatch):
    import skillberry_plugin_dast.plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "generator_available", lambda: False)
    p = SkillberryPluginDast()
    assert p.is_enabled() is False
    assert "Disabled" in p.get_status_message()


@pytest.mark.asyncio
async def test_is_ready_reports_missing_engine(monkeypatch):
    import skillberry_plugin_dast.plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "generator_available", lambda: False)
    p = SkillberryPluginDast()
    ready = await p.is_ready()
    assert ready["ready"] is False
    assert "input-generator-engine" in ready["missing_config"]


# ── router ────────────────────────────────────────────────────────────────────


def test_scan_endpoint_503_when_disabled(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import skillberry_plugin_dast.plugin as plugin_mod

    monkeypatch.setattr(plugin_mod, "generator_available", lambda: False)
    app = FastAPI()
    app.include_router(SkillberryPluginDast().get_router())
    client = TestClient(app)
    r = client.post("/scan", json={"object_type": "skill", "uuid": "x"})
    assert r.status_code == 503
    assert "Disabled" in r.json()["detail"]


def test_router_exposes_scan():
    p = SkillberryPluginDast()
    assert "/scan" in {r.path for r in p.get_router().routes}


def test_scan_status_endpoint_reports_progress():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from skillberry_plugin_dast.engine import progress

    app = FastAPI()
    app.include_router(SkillberryPluginDast().get_router())
    client = TestClient(app)

    # unknown uuid -> idle
    r = client.get("/scan-status", params={"uuid": "nope"})
    assert r.status_code == 200 and r.json()["state"] == "idle"

    # simulate an in-flight scan and confirm the label reflects the entry point
    progress.start("u9", total=4)
    progress.update("u9", current=2, total=4, entry_point="send_msg")
    try:
        r = client.get("/scan-status", params={"uuid": "u9"})
        body = r.json()
        assert body["state"] == "running"
        assert body["entry_point"] == "send_msg"
        assert "send_msg" in body["label"] and "2/4" in body["label"]
    finally:
        progress.clear("u9")


def test_endpoint_blank_input_400_not_422(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import skillberry_plugin_dast.plugin as plugin_mod

    # Force the engine enabled so validation (400) is reached rather than the
    # disabled gate (503) — this test is about input validation, not gating.
    monkeypatch.setattr(plugin_mod, "generator_available", lambda: True)
    app = FastAPI()
    app.include_router(SkillberryPluginDast().get_router())
    client = TestClient(app)
    r = client.post("/scan", json={})
    assert r.status_code == 400 and "uuid is required" in r.json()["detail"]
    r = client.post("/scan", json={"object_type": "widget", "uuid": "x"})
    assert r.status_code == 400 and "object_type must be one of" in r.json()["detail"]


# ── scan (dry-run, offline) ─────────────────────────────────────────────────────


@requires_engine
@pytest.mark.asyncio
async def test_scan_skill_discovers_and_persists(monkeypatch):
    monkeypatch.setenv("DAST_SCOPE", "discovered")  # exercise all tiers directly
    store = FakeAsyncStore(
        objects={
            ("skill", "sk1"): {
                "uuid": "sk1",
                "name": "demo",
                "tool_uuids": ["t1"],
                "snippet_uuids": [],
                "extra": {"other": "keep me"},
                "tags": ["x"],
            },
            ("tool", "t1"): {
                "uuid": "t1",
                "name": "send_msg",
                "module_name": "send.py",
                "params": {
                    "properties": {"channel": {"type": "string"}},
                    "required": ["channel"],
                    "optional": [],
                },
            },
        },
        modules={
            ("t1", "send.py"): (
                "def send_msg(channel):\n    return channel\n"
                "def helper(x):\n    return x\n"
            )
        },
    )
    p = _plugin(store, monkeypatch)
    result = await p.scan("skill", "sk1")
    block = result["dast"]

    # Tier-1 tool + Tier-2 helper discovered
    names = {e["name"] for e in block["entry_points"]}
    assert "send_msg" in names and "helper" in names
    assert block["coverage"]["entry_points_discovered"] >= 2
    assert block["scanner"]["mode"] == "detect-and-report"
    assert block["coverage"]["observation"] == "detected, not prevented"

    # persisted non-destructively + dast tags
    stored = await store.get_skill("sk1")
    assert stored["extra"]["dast"]["schema_version"] == 1
    assert stored["extra"]["other"] == "keep me"
    assert any(t.startswith("dast:coverage:") for t in stored["tags"])
    assert "x" in stored["tags"]


@pytest.mark.asyncio
async def test_resolve_execution_target_covers_all_tiers(monkeypatch):
    # The synthesis logic: tool runs as-is; function by name; class via factory;
    # __main__ via runner. Verify (func_name, source, manifest) per kind.
    from skillberry_plugin_dast.engine.base import EntryPoint

    src = (
        "def maintool(x):\n    return x\n"
        "def helper(y):\n    return y\n"
        "class Widget:\n    def __init__(self, n):\n        self.n = n\n"
    )
    store = FakeAsyncStore(
        objects={
            ("tool", "t1"): {"uuid": "t1", "name": "maintool", "module_name": "m.py"}
        },
        modules={("t1", "m.py"): src},
    )
    p = _plugin(store, monkeypatch)
    tools_by_name = {
        "maintool": {"uuid": "t1", "name": "maintool", "module_name": "m.py"}
    }
    module_to_source = {"m.py": src}
    module_to_tool = {"m.py": tools_by_name["maintool"]}

    def resolve(ep):
        return p._resolve_execution_target(
            ep, tools_by_name, module_to_source, module_to_tool
        )

    # Tier-1 tool -> its own function, original source
    fn, source, man = resolve(
        EntryPoint(name="maintool", kind="tool", module="m.py", tool_uuid="t1")
    )
    assert fn == "maintool" and "def maintool" in source

    # Tier-2 function -> by name
    fn, source, man = resolve(
        EntryPoint(name="helper", kind="function", module="m.py", signature=["y"])
    )
    assert fn == "helper" and man["name"] == "helper"

    # Tier-2 class -> factory appended, returns a serializable marker
    fn, source, man = resolve(
        EntryPoint(name="Widget", kind="class", module="m.py", signature=["n"])
    )
    assert fn == "__dast_make_Widget"
    assert "def __dast_make_Widget" in source
    assert "__dast_constructed:Widget" in source

    # unknown module -> None
    assert resolve(EntryPoint(name="x", kind="function", module="missing.py")) is None


def test_summary_message_separates_exercised_from_findings():
    # 96 MCP calls EXERCISED with 0 findings must NOT read as "96 findings found".
    from skillberry_plugin_dast.plugin import _summary_message

    block = {
        "summary": {
            "exercised": {"direct_calls": 0, "mcp_calls": 96, "total": 96},
            "findings": {"direct": 0, "mcp": 0, "total": 0, "high": 0, "medium": 0},
        }
    }
    msg = _summary_message(block)
    assert "Exercised 96 call" in msg
    assert "MCP: 96 call(s), 0 finding(s)" in msg
    assert "Total findings: 0" in msg


def test_summary_message_reports_direct_findings():
    from skillberry_plugin_dast.plugin import _summary_message

    block = {
        "summary": {
            "exercised": {"direct_calls": 10, "mcp_calls": 0, "total": 10},
            "findings": {"direct": 2, "mcp": 0, "total": 2, "high": 1, "medium": 1},
        }
    }
    msg = _summary_message(block)
    assert "direct: 10 call(s), 2 finding(s)" in msg
    assert "Total findings: 2 (high 1)" in msg


def test_env_knobs_parsed(monkeypatch):
    monkeypatch.setenv("DAST_MAX_CASES", "5")
    monkeypatch.setenv("DAST_EXEC_TIMEOUT", "7")
    p = SkillberryPluginDast()
    assert p._max_cases == 5
    assert p._exec_timeout == 7.0


def test_env_knobs_bad_values_fall_back(monkeypatch):
    monkeypatch.setenv("DAST_MAX_CASES", "not-an-int")
    monkeypatch.setenv("DAST_EXEC_TIMEOUT", "nope")
    p = SkillberryPluginDast()
    assert p._max_cases == 5  # small default for fast scans
    assert p._exec_timeout == 5.0  # small default


@requires_engine
@pytest.mark.asyncio
async def test_max_cases_env_limits_generated_cases(monkeypatch):
    monkeypatch.setenv("DAST_SCOPE", "registered")
    monkeypatch.setenv("DAST_MAX_CASES", "3")
    monkeypatch.delenv("DAST_LIVE", raising=False)  # dry-run executor
    store = FakeAsyncStore(
        objects={
            ("tool", "t1"): {
                "uuid": "t1",
                "name": "send",
                "module_name": "s.py",
                "params": {
                    "properties": {"a": {"type": "string"}},
                    "required": ["a"],
                    "optional": [],
                },
            }
        },
        modules={("t1", "s.py"): "def send(a):\n    return a\n"},
    )
    p = _plugin(store, monkeypatch)
    block = (await p.scan("tool", "t1"))["dast"]
    assert block["scanner"]["max_cases_per_entry"] == 3


@pytest.mark.asyncio
async def test_scan_missing_object_raises(monkeypatch):
    p = _plugin(FakeAsyncStore(), monkeypatch)
    with pytest.raises(ValueError):
        await p.scan("skill", "nope")


@pytest.mark.asyncio
async def test_scan_records_coverage_caveats(monkeypatch):
    store = FakeAsyncStore(
        objects={
            ("tool", "t1"): {
                "uuid": "t1",
                "name": "t",
                "module_name": "m.py",
                "params": {"properties": {}, "required": []},
            }
        },
        modules={("t1", "m.py"): "def t():\n    return 1\n"},
    )
    p = _plugin(store, monkeypatch)
    block = (await p.scan("tool", "t1"))["dast"]
    assert "static" in block["coverage"]["discovery"]
    assert block["scanner"]["live"] is False
