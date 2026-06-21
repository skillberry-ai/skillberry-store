"""Tests for the doc-generator plugin (mocked store + mocked LLM, no network).

The LLM is wired exactly like the security plugin, so these tests use the same
idiom: fake ``llm_switchboard`` at import time so the plugin builds a mock
client, then stub ``generate_async`` with an ``AsyncMock``.
"""

import copy
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from skillberry_plugin_doc_generator.plugin import SkillberryPluginDocGenerator
from skillberry_store.plugins import events as events_module
from skillberry_store.plugins.base import PluginType


class FakeStore:
    """Minimal in-memory store: get_/update_ for each object type round-trip.

    update_* writes back into the same dict so a later get_* observes the
    plugin's persistence (proposed/current blocks, tags).
    """

    def __init__(self, objects=None):
        # keyed by (object_type, uuid) -> dict
        self._objs = objects or {}

    # getters
    def get_skill(self, uuid):
        return copy.deepcopy(self._objs.get(("skill", uuid)))

    def get_tool(self, uuid):
        return copy.deepcopy(self._objs.get(("tool", uuid)))

    def get_snippet(self, uuid):
        return copy.deepcopy(self._objs.get(("snippet", uuid)))

    # writers
    def update_skill(self, uuid, data):
        self._objs[("skill", uuid)] = copy.deepcopy(data)
        return True

    def update_tool(self, uuid, data):
        self._objs[("tool", uuid)] = copy.deepcopy(data)
        return True

    def update_snippet(self, uuid, data):
        self._objs[("snippet", uuid)] = copy.deepcopy(data)
        return True


def _llm_json(description="Clear documentation produced for the object.", **extra):
    payload = {
        "description": description,
        "when_to_use": "When you need this capability.",
        "parameters": extra.get("parameters", []),
        "examples": extra.get("examples", ["example usage"]),
    }
    return json.dumps(payload)


def _make_plugin_with_mock_llm():
    """Create a plugin instance with a mocked (enabled) LLM client."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginDocGenerator()
    return plugin


def _plugin(store, response=None):
    """An enabled plugin bound to ``store`` with a canned LLM response."""
    p = _make_plugin_with_mock_llm()
    p.set_store_api(store)
    p.llm_client.generate_async = AsyncMock(return_value=response or _llm_json())
    return p


# ── metadata / enablement ────────────────────────────────────────────────────


def test_metadata_and_enablement():
    p = _make_plugin_with_mock_llm()
    assert p.metadata.name == "Documentation Generator"
    assert p.metadata.plugin_type == PluginType.EVALUATOR
    assert p.is_enabled() is True
    assert "Ready" in p.get_status_message()


def test_plugin_disabled_when_llm_unavailable():
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        p = SkillberryPluginDocGenerator()
    assert p.is_enabled() is False
    assert "error" in p.get_status_message().lower()


def test_router_exposes_generate_and_refresh():
    p = _make_plugin_with_mock_llm()
    router = p.get_router()
    paths = {r.path for r in router.routes}
    assert "/generate" in paths
    assert "/refresh" in paths


def test_ui_config_actions():
    p = _make_plugin_with_mock_llm()
    cfg = p.get_ui_config()
    labels = {a["label"] for a in cfg["actions"]}
    assert any("Generate" in label for label in labels)
    assert any("Refresh" in label for label in labels)
    # object_type must carry a default so the generic UI form pre-populates it.
    for action in cfg["actions"]:
        ot = action["params_schema"]["properties"]["object_type"]
        assert ot.get("default") == "tool"


# ── endpoint validation / gating ─────────────────────────────────────────────


def test_endpoint_validates_blank_and_bad_input_as_400_not_422():
    """The generic UI form may omit the enum field; we want a clean 400."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(_make_plugin_with_mock_llm().get_router())
    client = TestClient(app)

    # empty body: object_type defaults to 'tool', uuid missing -> 400 (not 422)
    r = client.post("/generate", json={})
    assert r.status_code == 400
    assert "uuid is required" in r.json()["detail"]

    # invalid object_type -> 400 with a helpful message
    r = client.post("/generate", json={"object_type": "widget", "uuid": "x"})
    assert r.status_code == 400
    assert "object_type must be one of" in r.json()["detail"]


def test_endpoint_returns_503_when_llm_unavailable():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginDocGenerator()

    app = FastAPI()
    app.include_router(plugin.get_router())
    client = TestClient(app)
    r = client.post("/generate", json={"object_type": "tool", "uuid": "t1"})
    assert r.status_code == 503


# ── parameter extraction (LLM-independent) ───────────────────────────────────


def test_list_parameter_schema_form_supported():
    store = FakeStore(
        {
            ("tool", "t1"): {
                "name": "t",
                "parameters": [
                    {
                        "name": "x",
                        "type": "string",
                        "required": True,
                        "description": "the x",
                    },
                ],
            }
        }
    )
    p = _plugin(store)
    obj = store.get_tool("t1")
    object_doc = p._to_object_doc("tool", "t1", obj)
    assert [pp.name for pp in object_doc.parameters] == ["x"]
    assert object_doc.parameters[0].description == "the x"


# ── core operations (mocked LLM) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_proposes_without_applying():
    store = FakeStore(
        {
            ("tool", "t1"): {
                "name": "send_msg",
                "parameters": {
                    "properties": {"channel": {"type": "string"}},
                    "required": ["channel"],
                },
            }
        }
    )
    p = _plugin(store)
    result = await p.generate_docs("tool", "t1", apply=False)

    assert result["applied"] is False
    doc = result["documentation"]
    assert doc["description"]
    assert doc["backend"] == p._backend and doc["backend"]
    assert "source_fingerprint" in doc

    # persisted under proposed, NOT current; author description untouched
    stored = store.get_tool("t1")
    block = stored["extra"]["documentation"]
    assert "proposed" in block and "current" not in block
    assert "description" not in stored  # raw field never written
    assert any(t == "doc:status:proposed" for t in stored["tags"])


@pytest.mark.asyncio
async def test_generate_apply_promotes_to_current():
    store = FakeStore({("snippet", "s1"): {"name": "retry_prompt", "content": "hi"}})
    p = _plugin(store)
    result = await p.generate_docs("snippet", "s1", apply=True)

    assert result["applied"] is True
    block = store.get_snippet("s1")["extra"]["documentation"]
    assert "current" in block and "proposed" not in block
    assert any(t == "doc:status:applied" for t in store.get_snippet("s1")["tags"])


@pytest.mark.asyncio
async def test_only_if_missing_skips_when_docs_applied():
    store = FakeStore({("tool", "t1"): {"name": "t", "content": "x"}})
    p = _plugin(store)
    await p.generate_docs("tool", "t1", apply=True)  # now has current docs
    result = await p.generate_docs("tool", "t1", apply=False, only_if_missing=True)
    assert result["applied"] is False
    assert result["skipped"]


@pytest.mark.asyncio
async def test_missing_object_raises_valueerror():
    p = _plugin(FakeStore())
    with pytest.raises(ValueError):
        await p.generate_docs("tool", "nope")


@pytest.mark.asyncio
async def test_generate_requires_llm_client():
    """With no LLM the operation hard-fails rather than silently degrading."""
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        p = SkillberryPluginDocGenerator()
    p.set_store_api(FakeStore({("tool", "t1"): {"name": "t"}}))
    with pytest.raises(RuntimeError, match="LLM client not initialized"):
        await p.generate_docs("tool", "t1")


@pytest.mark.asyncio
async def test_refresh_detects_no_drift_then_drift():
    store = FakeStore(
        {
            ("tool", "t1"): {
                "name": "t",
                "module_name": None,
                "parameters": {"properties": {"a": {"type": "string"}}, "required": []},
            }
        }
    )
    p = _plugin(store)
    await p.generate_docs("tool", "t1", apply=True)

    # No source change yet -> no drift.
    r1 = await p.refresh_docs("tool", "t1")
    assert r1["drift"] == []

    # Change the parameter schema -> source fingerprint changes -> drift.
    obj = store.get_tool("t1")
    obj["parameters"] = {
        "properties": {"a": {"type": "string"}, "b": {"type": "int"}},
        "required": ["b"],
    }
    store.update_tool("t1", obj)

    r2 = await p.refresh_docs("tool", "t1")
    assert r2["drift"]
    # refreshed docs are proposed (not applied) and re-generated
    assert r2["applied"] is False
    assert r2["documentation"]["backend"] == p._backend
    assert r2["documentation"]["source_fingerprint"] != (r1["documentation"] or {}).get(
        "source_fingerprint"
    )


@pytest.mark.asyncio
async def test_thin_author_description_labeled_enriched():
    store = FakeStore(
        {
            ("tool", "t1"): {
                "name": "fetch",
                "description": "Gets data",  # thin (< 40 chars)
                "content": "import requests",
            }
        }
    )
    p = _plugin(store)
    result = await p.generate_docs("tool", "t1", apply=True)
    assert result["documentation"]["mode"] == "enriched"


@pytest.mark.asyncio
async def test_substantial_author_description_kept_verbatim():
    author = "Posts a richly formatted message to a Slack channel and returns the ts."
    store = FakeStore({("tool", "t1"): {"name": "post", "description": author}})
    p = _plugin(store)
    result = await p.generate_docs("tool", "t1", apply=True)
    # non-destructive: sufficient author content is kept verbatim
    assert result["documentation"]["mode"] == "kept"
    assert result["documentation"]["description"] == author


# ── event handlers ───────────────────────────────────────────────────────────


def test_event_handlers_registered_for_all_content_types():
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        _make_plugin_with_mock_llm()
        assert len(events_module._event_handlers.get("content_added:tool", [])) > 0
        assert len(events_module._event_handlers.get("content_added:skill", [])) > 0
        assert len(events_module._event_handlers.get("content_added:snippet", [])) > 0
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_auto_proposal_skipped_when_store_not_set():
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        _make_plugin_with_mock_llm()  # store API never set
        handler = events_module._event_handlers["content_added:tool"][0]
        await handler(uuid="any-uuid")  # must not raise
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_auto_proposal_skipped_when_disabled():
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        mock_module = MagicMock()
        mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
        with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
            plugin = SkillberryPluginDocGenerator()
        plugin.set_store_api(FakeStore({("tool", "t1"): {"name": "t"}}))
        handler = events_module._event_handlers["content_added:tool"][0]
        await handler(uuid="t1")  # disabled -> must not raise or call LLM
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)
