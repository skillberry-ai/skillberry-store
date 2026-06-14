"""Tests for the SAST plugin."""

import contextlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skillberry_plugin_sast.engines.base import Finding, SastEngine
from skillberry_plugin_sast.plugin import SkillberryPluginSast
from skillberry_store.plugins.base import PluginType

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


@contextlib.contextmanager
def _make_plugin(engine=None, active_env=None, available_env=None):
    """Yield a plugin with the engine registry patched to a fake engine.

    The patch stays active for the whole `with` block, because the plugin
    resolves engines lazily on every call (is_enabled/scan_object), not just at
    construction time. ``active_env``/``available_env`` set the two SAST env vars
    for the duration; both are cleared otherwise so the host environment can't
    leak into the test.
    """
    engine = engine if engine is not None else _FakeEngine()
    registry = {engine.name: lambda e=engine: e}  # factory returning our instance
    # Default both SAST vars to empty (parsed as "unset") so the host env can't
    # leak in; override per-test as requested.
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
        yield SkillberryPluginSast()


def _mock_store(tool=None, skill=None, snippet=None):
    store = MagicMock()
    # Default the get_* probes to None so _infer_type resolves cleanly to the
    # one type that is provided.
    store.get_tool.return_value = tool
    store.get_skill.return_value = skill
    store.get_snippet.return_value = snippet
    store.tools = MagicMock()
    store.tools.read_file.return_value = "import os\neval(input())\n"
    store.tools.write_dict.return_value = {"success": True}
    store.skills = MagicMock()
    store.snippets = MagicMock()
    store.snippets.write_dict.return_value = {"success": True}
    return store


# ── metadata / enablement ────────────────────────────────────────────────────


def test_plugin_metadata():
    with _make_plugin() as plugin:
        md = plugin.metadata
        assert md.name == "SAST Scanner"
        assert md.plugin_type == PluginType.EVALUATOR
        assert md.version == "0.1.0"
        assert "static" in md.description.lower() or "sast" in md.description.lower()


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
    # Only "bandit" is implemented (the fake registry has just bandit), so an
    # available list naming an unimplemented engine drops it.
    with _make_plugin(available_env="bandit,semgrep") as plugin:
        assert plugin._available_engines == ["bandit"]


def test_active_constrained_to_available():
    # Active names an engine that isn't in the available set => dropped; falls
    # back to the available set rather than going inert.
    with _make_plugin(available_env="bandit", active_env="semgrep") as plugin:
        assert plugin._available_engines == ["bandit"]
        assert plugin._default_engines == ["bandit"]


def test_ui_config_has_simple_uuid_and_content_type_fields():
    with _make_plugin() as plugin:
        cfg = plugin.get_ui_config()
    props = cfg["actions"][0]["params_schema"]["properties"]
    assert props["uuid"]["type"] == "string"
    assert props["content_type"]["enum"] == ["tool", "skill", "snippet"]
    assert cfg["actions"][0]["params_schema"]["required"] == ["uuid"]


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
        "tags": ["python", "sast:clean"],
        "extra": {"evaluation": {"security": {"score": 4, "evaluation": "old"}}},
    }
    store = _mock_store(tool=tool)
    with _make_plugin(_FakeEngine(findings=[finding])) as plugin:
        plugin.set_store_api(store)
        result = await plugin.scan_object("tool-1", "tool")

    assert result["summary"]["high"] == 1
    assert result["engines"]["bandit"]["status"] == "ok"

    # write_dict was called; inspect what we persisted.
    written = store.tools.write_dict.call_args[0][1]
    assert written["extra"]["evaluation"]["sast"]["summary"]["high"] == 1
    # security evaluation preserved, not clobbered:
    assert written["extra"]["evaluation"]["security"]["score"] == 4
    # old sast tag replaced by new summary tag:
    assert "sast:clean" not in written["tags"]
    assert "sast:high:1" in written["tags"]
    assert "python" in written["tags"]


@pytest.mark.asyncio
async def test_scan_object_reports_missing_engine():
    with _make_plugin(_FakeEngine(available=False)) as plugin:
        plugin.set_store_api(
            _mock_store(
                tool={
                    "uuid": "t",
                    "name": "x",
                    "programming_language": "python",
                    "module_name": "tool.py",
                    "tags": [],
                    "extra": {},
                }
            )
        )
        result = await plugin.scan_object("t", "tool", engines=["bandit"])
    assert result["engines"]["bandit"]["status"] == "not_installed"


@pytest.mark.asyncio
async def test_scan_object_reports_unknown_engine():
    with _make_plugin() as plugin:
        plugin.set_store_api(
            _mock_store(
                tool={
                    "uuid": "t",
                    "name": "x",
                    "programming_language": "python",
                    "module_name": "tool.py",
                    "tags": [],
                    "extra": {},
                }
            )
        )
        result = await plugin.scan_object("t", "tool", engines=["nosuchengine"])
    assert result["engines"]["nosuchengine"]["status"] == "unknown_engine"


@pytest.mark.asyncio
async def test_scan_object_missing_object_raises_valueerror():
    with _make_plugin() as plugin:
        plugin.set_store_api(_mock_store(tool=None))
        with pytest.raises(ValueError):
            await plugin.scan_object("missing", "tool")


# ── type inference ───────────────────────────────────────────────────────────


def test_infer_type_probes_each_store_accessor():
    with _make_plugin() as plugin:
        plugin.set_store_api(_mock_store(tool={"uuid": "t"}))
        assert plugin._infer_type("t") == "tool"

        plugin.set_store_api(_mock_store(skill={"uuid": "s"}))
        assert plugin._infer_type("s") == "skill"

        plugin.set_store_api(_mock_store(snippet={"uuid": "n"}))
        assert plugin._infer_type("n") == "snippet"

        plugin.set_store_api(_mock_store())  # all None
        assert plugin._infer_type("missing") is None


@pytest.mark.asyncio
async def test_scan_object_infers_type_when_omitted():
    tool = {
        "uuid": "t",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "tags": [],
        "extra": {},
    }
    with _make_plugin(_FakeEngine(findings=[])) as plugin:
        plugin.set_store_api(_mock_store(tool=tool))
        result = await plugin.scan_object("t")  # no content_type
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
        "tags": [],
        "extra": {},
    }
    store = _mock_store()
    # Key the tool lookup on uuid so "ghost" genuinely resolves to nothing.
    store.get_tool.side_effect = lambda u: tool if u == "t1" else None
    with _make_plugin(_FakeEngine(findings=[finding])) as plugin:
        plugin.set_store_api(store)
        # "t1" resolves to the tool; "ghost" resolves to nothing.
        result = await plugin.scan_objects(["t1", "ghost"])

    assert result["not_found"] == ["ghost"]
    assert len(result["results"]) == 1
    assert result["summary"]["high"] == 1


@pytest.mark.asyncio
async def test_scan_objects_skill_fans_out_to_children():
    # A store where the skill references one tool and one snippet.
    skill = {"uuid": "sk", "name": "s", "tool_uuids": ["t1"], "snippet_uuids": ["n1"]}
    tool = {
        "uuid": "t1",
        "name": "tool",
        "programming_language": "python",
        "module_name": "tool.py",
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

    store = MagicMock()
    store.get_skill.side_effect = lambda u: skill if u == "sk" else None
    store.get_tool.side_effect = lambda u: tool if u == "t1" else None
    store.get_snippet.side_effect = lambda u: snippet if u == "n1" else None
    store.tools = MagicMock()
    store.tools.read_file.return_value = "eval(input())\n"
    store.tools.write_dict.return_value = {"success": True}
    store.snippets = MagicMock()
    store.snippets.write_dict.return_value = {"success": True}

    with _make_plugin(_FakeEngine(findings=[])) as plugin:
        plugin.set_store_api(store)
        result = await plugin.scan_objects(["sk"])

    scanned_types = sorted(r["content_type"] for r in result["results"])
    # skill itself (no code) + its tool + its snippet
    assert scanned_types == ["skill", "snippet", "tool"]
    # skill aggregate written back
    assert store.skills.write_dict.called


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
        "tags": [],
        "extra": {},
    }

    store = MagicMock()
    store.get_skill.side_effect = lambda u: skill if u == "sk" else None
    store.get_tool.side_effect = lambda u: tool if u == "t1" else None
    store.get_snippet.return_value = None
    store.tools = MagicMock()
    store.tools.read_file.return_value = "assert False\n"
    store.tools.write_dict.return_value = {"success": True}
    store.snippets = MagicMock()
    store.snippets.write_dict.return_value = {"success": True}
    store.skills = MagicMock()
    store.skills.write_dict.return_value = {"success": True}

    with _make_plugin(_FakeEngine(findings=[finding])) as plugin:
        plugin.set_store_api(store)
        await plugin.scan_objects(["sk"])

    # skills.write_dict must have been called with the skill's uuid
    assert store.skills.write_dict.called
    written_obj = store.skills.write_dict.call_args[0][1]
    assert written_obj["extra"]["evaluation"]["sast"]["summary"]["high"] == 1
    assert any(t.startswith("sast:high:") for t in written_obj["tags"])


# ── event handlers ───────────────────────────────────────────────────────────


def test_event_handlers_registered():
    from skillberry_store.plugins import events as events_module

    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        with _make_plugin():
            for ct in ("tool", "skill", "snippet"):
                assert (
                    len(events_module._event_handlers.get(f"content_added:{ct}", []))
                    > 0
                )
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


# ── router ───────────────────────────────────────────────────────────────────


def _client(plugin):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/sast")
    return TestClient(app)


def test_router_scan_missing_uuid_422():
    with _make_plugin(_FakeEngine(available=True)) as plugin:
        plugin.set_store_api(_mock_store(tool={"uuid": "t"}))
        resp = _client(plugin).post("/plugins/sast/scan", json={})
        assert resp.status_code == 422


def test_router_scan_disabled_503():
    with _make_plugin(_FakeEngine(available=False)) as plugin:
        plugin.set_store_api(_mock_store(tool={"uuid": "t"}))
        resp = _client(plugin).post("/plugins/sast/scan", json={"uuid": "t"})
        assert resp.status_code == 503


def test_router_scan_missing_object_404():
    with _make_plugin(_FakeEngine(available=True)) as plugin:
        plugin.set_store_api(_mock_store())  # nothing resolves
        resp = _client(plugin).post("/plugins/sast/scan", json={"uuid": "missing"})
        assert resp.status_code == 404


def test_router_scan_ok_infers_type_200():
    tool = {
        "uuid": "t",
        "name": "x",
        "programming_language": "python",
        "module_name": "tool.py",
        "tags": [],
        "extra": {},
    }
    with _make_plugin(_FakeEngine(available=True, findings=[])) as plugin:
        plugin.set_store_api(_mock_store(tool=tool))
        resp = _client(plugin).post("/plugins/sast/scan", json={"uuid": "t"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["content_type"] == "tool"


# ── ui_config ─────────────────────────────────────────────────────────────────




# ── LLM fix ───────────────────────────────────────────────────────────────────


def _tool(uuid="t1", tags=None):
    return {
        "uuid": uuid,
        "name": "bad_tool",
        "programming_language": "python",
        "module_name": "tool.py",
        "tags": tags or [],
        "extra": {},
    }


def test_fix_unavailable_without_llm():
    # llm-switchboard is not installed in the test env, so _llm is None.
    with _make_plugin() as plugin:
        assert plugin._fix_available() is False


@pytest.mark.asyncio
async def test_router_fix_disabled_503_without_llm():
    with _make_plugin(_FakeEngine(available=True)) as plugin:
        plugin.set_store_api(_mock_store(tool=_tool()))
        resp = _client(plugin).post("/plugins/sast/fix", json={"object_uuids": ["t1"]})
        assert resp.status_code == 503


@pytest.mark.asyncio
async def test_fix_object_writes_code_and_records_extra():
    finding = Finding(
        engine="bandit", rule_id="B307", severity="high", message="eval", line=2
    )
    tool = _tool()
    store = _mock_store(tool=tool)
    with _make_plugin(_FakeEngine(findings=[finding])) as plugin:
        plugin.set_store_api(store)
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(return_value="print('fixed')\n")

        result = await plugin.fix_object("t1", severities=["high"])

    assert result["status"] == "fixed"
    assert result["new_code"] == "print('fixed')\n"
    # code overwritten in the tool's module file
    store.tools.write_file.assert_called_once()
    assert store.tools.write_file.call_args[0][2] == "print('fixed')\n"
    # fix recorded in extra
    written = store.tools.write_dict.call_args[0][1]
    assert written["extra"]["evaluation"]["sast_fix"]["model"]
    assert "high" in written["extra"]["evaluation"]["sast_fix"]["severities"]


@pytest.mark.asyncio
async def test_fix_object_strips_markdown_fence():
    finding = Finding(
        engine="bandit", rule_id="B307", severity="high", message="x", line=1
    )
    with _make_plugin(_FakeEngine(findings=[finding])) as plugin:
        plugin.set_store_api(_mock_store(tool=_tool()))
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(
            return_value="```python\nprint('ok')\n```"
        )
        result = await plugin.fix_object("t1", severities=["high"])
    assert result["new_code"] == "print('ok')"


@pytest.mark.asyncio
async def test_fix_object_no_matching_findings():
    # finding is low; we ask to fix only high → nothing to fix.
    finding = Finding(
        engine="bandit", rule_id="B101", severity="low", message="x", line=1
    )
    with _make_plugin(_FakeEngine(findings=[finding])) as plugin:
        plugin.set_store_api(_mock_store(tool=_tool()))
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(return_value="should not be called")
        result = await plugin.fix_object("t1", severities=["high"])
    assert result["status"] == "no_matching_findings"
    plugin._llm.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_fix_objects_skips_skill():
    skill = {"uuid": "sk", "name": "s", "tool_uuids": [], "snippet_uuids": []}
    store = _mock_store(skill=skill)
    with _make_plugin(_FakeEngine(findings=[])) as plugin:
        plugin.set_store_api(store)
        plugin._llm = MagicMock()
        plugin._llm.generate_async = AsyncMock(return_value="x")
        result = await plugin.fix_objects(["sk"])
    assert result["results"][0]["status"] == "no_code"
