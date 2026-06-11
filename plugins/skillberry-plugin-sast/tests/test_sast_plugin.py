"""Tests for the SAST plugin."""

import contextlib
import os
from unittest.mock import MagicMock, patch

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
def _make_plugin(engine=None, env_engines=None):
    """Yield a plugin with the engine registry patched to a fake engine.

    The patch stays active for the whole `with` block, because the plugin
    resolves engines lazily on every call (is_enabled/scan_object), not just at
    construction time.
    """
    engine = engine if engine is not None else _FakeEngine()
    registry = {engine.name: lambda e=engine: e}  # factory returning our instance
    env = {}
    if env_engines is not None:
        env["SBS_SAST_ENGINES"] = env_engines
    with (
        patch.dict(
            "skillberry_plugin_sast.engines.ENGINE_REGISTRY", registry, clear=True
        ),
        patch.dict(os.environ, env, clear=False),
    ):
        yield SkillberryPluginSast()


def _mock_store(tool=None):
    store = MagicMock()
    store.get_tool.return_value = tool
    store.tools = MagicMock()
    store.tools.read_file.return_value = "import os\neval(input())\n"
    store.tools.write_dict.return_value = {"success": True}
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


def test_default_engines_from_env():
    with _make_plugin(env_engines="bandit") as plugin:
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


def test_router_scan_bad_content_type_400():
    with _make_plugin(_FakeEngine(available=True)) as plugin:
        plugin.set_store_api(_mock_store(tool={"uuid": "t"}))
        resp = _client(plugin).post(
            "/plugins/sast/scan", json={"uuid": "t", "content_type": "widget"}
        )
        assert resp.status_code == 400


def test_router_scan_disabled_503():
    with _make_plugin(_FakeEngine(available=False)) as plugin:
        plugin.set_store_api(_mock_store(tool={"uuid": "t"}))
        resp = _client(plugin).post(
            "/plugins/sast/scan", json={"uuid": "t", "content_type": "tool"}
        )
        assert resp.status_code == 503


def test_router_scan_missing_object_404():
    with _make_plugin(_FakeEngine(available=True)) as plugin:
        plugin.set_store_api(_mock_store(tool=None))
        resp = _client(plugin).post(
            "/plugins/sast/scan", json={"uuid": "missing", "content_type": "tool"}
        )
        assert resp.status_code == 404
