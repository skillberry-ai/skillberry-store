"""Tests for the SAST plugin (SDK-based, out-of-process)."""

import contextlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skillberry_plugin_sast.engines.base import Finding, SastEngine
from skillberry_plugin_sast.plugin import SkillberryPluginSast
from skillberry_plugin_sdk.testing import dummy_event

# ── fake engine so plugin tests don't need bandit installed ──────────────────


class _FakeEngine(SastEngine):
    name = "bandit"  # masquerade as bandit so default-engine resolution works
    languages = ("python",)

    def __init__(self, available=True, findings=None):
        self._available = available
        self._findings = findings or []

    def is_available(self):
        return self._available

    def scan(self, code, *, filename, language=None):
        return list(self._findings)


def _mock_store(tool=None, skill=None, snippet=None):
    """AsyncMock StoreClient — mirrors the SDK's REST-based surface."""
    store = AsyncMock()
    store.get_tool = AsyncMock(return_value=tool)
    store.get_skill = AsyncMock(return_value=skill)
    store.get_snippet = AsyncMock(return_value=snippet)
    store.update_tool = AsyncMock(return_value={"success": True})
    store.update_skill = AsyncMock(return_value={"success": True})
    store.update_snippet = AsyncMock(return_value={"success": True})
    return store


@contextlib.contextmanager
def _make_plugin(engine=None, active_env=None, available_env=None, store=None):
    """Yield a plugin with the engine registry patched to a fake engine.

    The patch stays active for the whole `with` block, because the plugin
    resolves engines lazily on every call (is_enabled/scan_object), not just at
    construction time. ``active_env``/``available_env`` set the two SAST env vars
    for the duration; both are cleared otherwise so the host environment can't
    leak into the test.
    """
    engine = engine if engine is not None else _FakeEngine()
    registry = {engine.name: lambda e=engine: e}  # factory returning our instance
    env = {
        "SBS_SAST_ACTIVE_ENGINES": active_env or "",
        "SBS_SAST_AVAILABLE_ENGINES": available_env or "",
    }
    with (
        patch.dict(
            "skillberry_plugin_sast.engines.ENGINE_REGISTRY", registry, clear=True
        ),
        patch.dict(os.environ, env, clear=False),
    ):
        plugin = SkillberryPluginSast()
        if store is not None:
            plugin._store = store
        yield plugin


# ── manifest / enablement ────────────────────────────────────────────────────


def test_plugin_manifest_slug():
    with _make_plugin() as plugin:
        assert plugin.manifest.slug == "sast"


def test_plugin_manifest_type_evaluator():
    with _make_plugin() as plugin:
        assert plugin.manifest.plugin_type == "evaluator"


def test_plugin_manifest_version():
    with _make_plugin() as plugin:
        assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_has_api():
    with _make_plugin() as plugin:
        assert plugin.manifest.has_api is True


def test_is_enabled_true_when_engine_available():
    with _make_plugin(_FakeEngine(available=True)) as plugin:
        assert plugin.is_enabled() is True


def test_is_enabled_false_when_engine_missing():
    with _make_plugin(_FakeEngine(available=False)) as plugin:
        assert plugin.is_enabled() is False


# ── tag helpers ──────────────────────────────────────────────────────────────


def test_strip_sast_tags_removes_only_sast():
    with _make_plugin() as plugin:
        tags = ["python", "sast:high:2", "security-score:4", "sast:clean"]
        assert plugin._strip_sast_tags(tags) == ["python", "security-score:4"]


def test_summary_tags_clean_when_empty():
    with _make_plugin() as plugin:
        assert plugin._summary_tags(
            {"low": 0, "medium": 0, "high": 0, "critical": 0}
        ) == ["sast:clean"]


def test_summary_tags_counts():
    with _make_plugin() as plugin:
        tags = plugin._summary_tags({"low": 1, "medium": 0, "high": 2, "critical": 0})
        assert "sast:low:1" in tags and "sast:high:2" in tags


# ── engine selection precedence ──────────────────────────────────────────────


def test_active_engines_default_to_bandit():
    with _make_plugin() as plugin:
        assert plugin._default_engines == ["bandit"]
        assert plugin._available_engines == ["bandit"]


def test_active_engines_from_env():
    with _make_plugin(active_env="bandit") as plugin:
        assert plugin._default_engines == ["bandit"]


def test_available_env_intersects_with_implemented():
    with _make_plugin(available_env="bandit,semgrep") as plugin:
        assert plugin._available_engines == ["bandit"]


def test_active_constrained_to_available():
    with _make_plugin(available_env="bandit", active_env="semgrep") as plugin:
        assert plugin._available_engines == ["bandit"]
        assert plugin._default_engines == ["bandit"]


# ── scan_object ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_object_writes_findings_and_preserves_security():
    finding = Finding(
        engine="bandit",
        rule_id="B307",
        severity="high",
        message="use of eval",
        line=2,
        snippet="eval(input())",
    )
    tool = {
        "uuid": "tool-1",
        "name": "bad_tool",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "import os\neval(input())\n",
        "tags": ["python", "sast:clean"],
        "extra": {"evaluation": {"security": {"score": 4, "evaluation": "old"}}},
    }
    store = _mock_store(tool=tool)
    with _make_plugin(_FakeEngine(findings=[finding]), store=store) as plugin:
        result = await plugin.scan_object("tool-1", "tool")

    assert result["summary"]["high"] == 1
    assert result["engines"]["bandit"]["status"] == "ok"

    store.update_tool.assert_awaited_once()
    written = store.update_tool.call_args[0][1]
    assert written["extra"]["evaluation"]["sast"]["summary"]["high"] == 1
    # security evaluation preserved, not clobbered:
    assert written["extra"]["evaluation"]["security"]["score"] == 4
    # old sast tag replaced by new summary tag:
    assert "sast:clean" not in written["tags"]
    assert "sast:high:1" in written["tags"]
    assert "python" in written["tags"]


@pytest.mark.asyncio
async def test_scan_object_reports_missing_engine():
    tool = {
        "uuid": "t",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "print(1)\n",
        "tags": [],
        "extra": {},
    }
    with _make_plugin(_FakeEngine(available=False), store=_mock_store(tool=tool)) as plugin:
        result = await plugin.scan_object("t", "tool", engines=["bandit"])
    assert result["engines"]["bandit"]["status"] == "not_installed"


@pytest.mark.asyncio
async def test_scan_object_reports_unknown_engine():
    tool = {
        "uuid": "t",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "print(1)\n",
        "tags": [],
        "extra": {},
    }
    with _make_plugin(store=_mock_store(tool=tool)) as plugin:
        result = await plugin.scan_object("t", "tool", engines=["nosuchengine"])
    assert result["engines"]["nosuchengine"]["status"] == "unknown_engine"


@pytest.mark.asyncio
async def test_scan_object_missing_object_raises_valueerror():
    with _make_plugin(store=_mock_store(tool=None)) as plugin:
        with pytest.raises(ValueError):
            await plugin.scan_object("missing", "tool")


# ── type inference ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_infer_type_probes_each_store_accessor():
    with _make_plugin(store=_mock_store(tool={"uuid": "t"})) as plugin:
        assert await plugin._infer_type("t") == "tool"

    with _make_plugin(store=_mock_store(skill={"uuid": "s"})) as plugin:
        assert await plugin._infer_type("s") == "skill"

    with _make_plugin(store=_mock_store(snippet={"uuid": "n"})) as plugin:
        assert await plugin._infer_type("n") == "snippet"

    with _make_plugin(store=_mock_store()) as plugin:  # all None
        assert await plugin._infer_type("missing") is None


@pytest.mark.asyncio
async def test_scan_object_infers_type_when_omitted():
    tool = {
        "uuid": "t",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "x = 1\n",
        "tags": [],
        "extra": {},
    }
    with _make_plugin(_FakeEngine(findings=[]), store=_mock_store(tool=tool)) as plugin:
        result = await plugin.scan_object("t")
    assert result["content_type"] == "tool"


# ── scan_objects (batch + inference + skill fan-out) ──────────────────────────


@pytest.mark.asyncio
async def test_scan_objects_batch_mixed_valid_and_missing():
    finding = Finding(
        engine="bandit", rule_id="B307", severity="high", message="eval", line=1
    )
    tool = {
        "uuid": "t1",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "eval(input())\n",
        "tags": [],
        "extra": {},
    }
    store = _mock_store()
    store.get_tool = AsyncMock(side_effect=lambda u: tool if u == "t1" else None)
    with _make_plugin(_FakeEngine(findings=[finding]), store=store) as plugin:
        result = await plugin.scan_objects(["t1", "ghost"])

    assert result["not_found"] == ["ghost"]
    assert len(result["results"]) == 1
    assert result["summary"]["high"] == 1


@pytest.mark.asyncio
async def test_scan_objects_skill_fans_out_to_children():
    skill = {"uuid": "sk", "name": "s", "tool_uuids": ["t1"], "snippet_uuids": ["n1"]}
    tool = {
        "uuid": "t1",
        "name": "tool",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "eval(input())\n",
        "tags": [],
        "extra": {},
    }
    snippet = {
        "uuid": "n1",
        "name": "snip",
        "content": "eval(input())",
        "content_type": "python",
        "tags": [],
        "extra": {},
    }

    store = AsyncMock()
    store.get_skill = AsyncMock(side_effect=lambda u: skill if u == "sk" else None)
    store.get_tool = AsyncMock(side_effect=lambda u: tool if u == "t1" else None)
    store.get_snippet = AsyncMock(side_effect=lambda u: snippet if u == "n1" else None)
    store.update_tool = AsyncMock(return_value={"success": True})
    store.update_skill = AsyncMock(return_value={"success": True})
    store.update_snippet = AsyncMock(return_value={"success": True})

    with _make_plugin(_FakeEngine(findings=[]), store=store) as plugin:
        result = await plugin.scan_objects(["sk"])

    scanned_types = sorted(r["content_type"] for r in result["results"])
    # skill itself (no code) + its tool + its snippet
    assert scanned_types == ["skill", "snippet", "tool"]
    # skill aggregate written back
    store.update_skill.assert_awaited()


@pytest.mark.asyncio
async def test_scan_objects_writes_skill_aggregate_tags_and_extra():
    """After scanning a skill's children, the skill gets sast tags and extra."""
    skill = {
        "uuid": "sk",
        "name": "s",
        "tool_uuids": ["t1"],
        "snippet_uuids": [],
        "tags": [],
        "extra": {},
    }
    finding = Finding(
        engine="bandit",
        rule_id="B101",
        severity="high",
        message="assert used",
        line=1,
    )
    tool = {
        "uuid": "t1",
        "name": "tool",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "assert False\n",
        "tags": [],
        "extra": {},
    }

    store = AsyncMock()
    store.get_skill = AsyncMock(side_effect=lambda u: skill if u == "sk" else None)
    store.get_tool = AsyncMock(side_effect=lambda u: tool if u == "t1" else None)
    store.get_snippet = AsyncMock(return_value=None)
    store.update_tool = AsyncMock(return_value={"success": True})
    store.update_skill = AsyncMock(return_value={"success": True})
    store.update_snippet = AsyncMock(return_value={"success": True})

    with _make_plugin(_FakeEngine(findings=[finding]), store=store) as plugin:
        await plugin.scan_objects(["sk"])

    store.update_skill.assert_awaited()
    written_obj = store.update_skill.call_args[0][1]
    assert written_obj["extra"]["evaluation"]["sast"]["summary"]["high"] == 1
    assert any(t.startswith("sast:high:") for t in written_obj["tags"])


# ── event handlers ───────────────────────────────────────────────────────────


def test_event_handlers_registered():
    from skillberry_plugin_sdk.decorators import get_event_handlers

    with _make_plugin() as plugin:
        handlers = get_event_handlers(plugin)
    assert "content.tool.added" in handlers
    assert "content.skill.added" in handlers
    assert "content.snippet.added" in handlers


@pytest.mark.asyncio
async def test_on_tool_added_triggers_scan():
    tool = {
        "uuid": "t1",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "print(1)\n",
        "tags": [],
        "extra": {},
    }
    store = _mock_store(tool=tool)
    with _make_plugin(_FakeEngine(findings=[]), store=store) as plugin:
        await plugin._on_tool_added(dummy_event("content.tool.added", {"uuid": "t1"}))
    store.get_tool.assert_awaited_with("t1")


@pytest.mark.asyncio
async def test_on_skill_added_fans_out_to_children():
    skill = {"uuid": "sk", "name": "s", "tool_uuids": ["t1"], "snippet_uuids": []}
    tool = {
        "uuid": "t1",
        "name": "tool",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "print(1)\n",
        "tags": [],
        "extra": {},
    }
    store = AsyncMock()
    store.get_skill = AsyncMock(return_value=skill)
    store.get_tool = AsyncMock(return_value=tool)
    store.get_snippet = AsyncMock(return_value=None)
    store.update_tool = AsyncMock(return_value={"success": True})
    store.update_skill = AsyncMock(return_value={"success": True})
    store.update_snippet = AsyncMock(return_value={"success": True})

    with _make_plugin(_FakeEngine(findings=[]), store=store) as plugin:
        await plugin._on_skill_added(dummy_event("content.skill.added", {"uuid": "sk"}))

    # tool should have been fetched for the child scan, and skill aggregate written
    store.get_tool.assert_awaited_with("t1")
    store.update_skill.assert_awaited()


# ── router ───────────────────────────────────────────────────────────────────


def _client(plugin):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(plugin.get_router())
    return TestClient(app)


def test_router_scan_missing_uuid_422():
    with _make_plugin(_FakeEngine(available=True), store=_mock_store(tool={"uuid": "t"})) as plugin:
        resp = _client(plugin).post("/plugins/sast/scan", json={})
        assert resp.status_code == 422


def test_router_scan_disabled_503():
    with _make_plugin(_FakeEngine(available=False), store=_mock_store(tool={"uuid": "t"})) as plugin:
        resp = _client(plugin).post("/plugins/sast/scan", json={"uuid": "t"})
        assert resp.status_code == 503


def test_router_scan_missing_object_404():
    with _make_plugin(_FakeEngine(available=True), store=_mock_store()) as plugin:
        resp = _client(plugin).post("/plugins/sast/scan", json={"uuid": "missing"})
        assert resp.status_code == 404


def test_router_scan_ok_infers_type_200():
    tool = {
        "uuid": "t",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "x = 1\n",
        "tags": [],
        "extra": {},
    }
    with _make_plugin(_FakeEngine(available=True, findings=[]), store=_mock_store(tool=tool)) as plugin:
        resp = _client(plugin).post("/plugins/sast/scan", json={"uuid": "t"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["content_type"] == "tool"


# ── LLM fix ───────────────────────────────────────────────────────────────────


def _tool(uuid="t1", tags=None):
    return {
        "uuid": uuid,
        "name": "bad_tool",
        "programming_language": "python",
        "module_name": "tool.py",
        "code": "eval(input())\n",
        "tags": tags or [],
        "extra": {},
    }


def test_fix_unavailable_without_llm():
    with _make_plugin() as plugin:
        plugin._llm = None
        assert plugin._fix_available() is False


def test_router_fix_disabled_503_without_llm():
    with _make_plugin(_FakeEngine(available=True), store=_mock_store(tool=_tool())) as plugin:
        plugin._llm = None
        resp = _client(plugin).post("/plugins/sast/fix", json={"object_uuids": ["t1"]})
        assert resp.status_code == 503


@pytest.mark.asyncio
async def test_fix_object_writes_code_and_records_extra():
    finding = Finding(
        engine="bandit", rule_id="B307", severity="high", message="eval", line=2
    )
    tool = _tool()
    store = _mock_store(tool=tool)
    with _make_plugin(_FakeEngine(findings=[finding]), store=store) as plugin:
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(return_value="print('fixed')\n")

        result = await plugin.fix_object("t1", severities=["high"])

    assert result["status"] == "fixed"
    assert result["new_code"] == "print('fixed')\n"
    # code overwritten via update_tool (REST PUT) with new code embedded
    store.update_tool.assert_awaited()
    written = store.update_tool.call_args[0][1]
    assert written["code"] == "print('fixed')\n"
    assert written["extra"]["evaluation"]["sast_fix"]["model"]
    assert "high" in written["extra"]["evaluation"]["sast_fix"]["severities"]


@pytest.mark.asyncio
async def test_fix_object_strips_markdown_fence():
    finding = Finding(
        engine="bandit", rule_id="B307", severity="high", message="x", line=1
    )
    with _make_plugin(_FakeEngine(findings=[finding]), store=_mock_store(tool=_tool())) as plugin:
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(
            return_value="```python\nprint('ok')\n```"
        )
        result = await plugin.fix_object("t1", severities=["high"])
    assert result["new_code"] == "print('ok')"


@pytest.mark.asyncio
async def test_fix_object_no_matching_findings():
    finding = Finding(
        engine="bandit", rule_id="B101", severity="low", message="x", line=1
    )
    with _make_plugin(_FakeEngine(findings=[finding]), store=_mock_store(tool=_tool())) as plugin:
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(return_value="should not be called")
        result = await plugin.fix_object("t1", severities=["high"])
    assert result["status"] == "no_matching_findings"
    plugin._llm.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_fix_objects_skips_skill():
    skill = {"uuid": "sk", "name": "s", "tool_uuids": [], "snippet_uuids": []}
    store = _mock_store(skill=skill)
    with _make_plugin(_FakeEngine(findings=[]), store=store) as plugin:
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(return_value="x")
        result = await plugin.fix_objects(["sk"])
    assert result["results"][0]["status"] == "no_code"
