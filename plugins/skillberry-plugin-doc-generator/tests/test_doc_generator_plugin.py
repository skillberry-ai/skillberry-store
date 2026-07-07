"""Tests for the doc-generator plugin (mocked store + mocked LLM, no network).

The plugin now inherits ``PluginLifecycleBase``; the LLM client is initialized
in ``on_start`` at runtime, but tests bypass that and assign a mock client
directly. The store is a small in-memory async fake that mirrors the SDK's
``StoreClient`` surface (``async get_*`` / ``update_*``).
"""

import copy
import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from skillberry_plugin_doc_generator.plugin import SkillberryPluginDocGenerator
from skillberry_plugin_sdk.testing import dummy_event


class FakeStore:
    """Async in-memory store mirroring the SDK StoreClient surface.

    ``update_*`` writes back into the same dict so a later ``get_*`` observes
    the plugin's persistence (proposed/current blocks, tags).
    """

    def __init__(self, objects=None):
        # keyed by (object_type, uuid) -> dict
        self._objs = objects or {}

    async def get_skill(self, uuid):
        return copy.deepcopy(self._objs.get(("skill", uuid)))

    async def get_tool(self, uuid):
        return copy.deepcopy(self._objs.get(("tool", uuid)))

    async def get_snippet(self, uuid):
        return copy.deepcopy(self._objs.get(("snippet", uuid)))

    async def update_skill(self, uuid, data):
        self._objs[("skill", uuid)] = copy.deepcopy(data)
        return data

    async def update_tool(self, uuid, data):
        self._objs[("tool", uuid)] = copy.deepcopy(data)
        return data

    async def update_snippet(self, uuid, data):
        self._objs[("snippet", uuid)] = copy.deepcopy(data)
        return data


def _llm_json(description="Clear documentation produced for the object.", **extra):
    payload = {
        "description": description,
        "when_to_use": "When you need this capability.",
        "parameters": extra.get("parameters", []),
        "examples": extra.get("examples", ["example usage"]),
    }
    return json.dumps(payload)


def _make_plugin_with_mock_llm():
    """Create a plugin with a mocked (enabled) LLM client bypassing on_start."""
    plugin = SkillberryPluginDocGenerator()
    plugin.llm_client = MagicMock()
    plugin._backend = "mock:mock"
    plugin._status_message = "Ready (using mock; review-before-apply)"
    return plugin


def _plugin(store, response=None):
    """An enabled plugin bound to ``store`` with a canned LLM response."""
    p = _make_plugin_with_mock_llm()
    p._store = store
    p.llm_client.generate_async = AsyncMock(return_value=response or _llm_json())
    return p


# ── manifest ─────────────────────────────────────────────────────────────────


def test_plugin_manifest_slug():
    p = SkillberryPluginDocGenerator()
    assert p.manifest.slug == "doc-generator"


def test_plugin_manifest_name():
    p = SkillberryPluginDocGenerator()
    assert p.manifest.name == "Documentation Generator"


def test_plugin_manifest_version():
    p = SkillberryPluginDocGenerator()
    assert p.manifest.version == "0.1.0"


def test_plugin_manifest_has_api():
    p = SkillberryPluginDocGenerator()
    assert p.manifest.has_api is True


def test_plugin_manifest_type_creator():
    p = SkillberryPluginDocGenerator()
    assert p.manifest.plugin_type == "creator"


# ── readiness ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_ready_true_when_llm_and_env_present(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai.async")
    p = _make_plugin_with_mock_llm()
    ready = await p.is_ready()
    assert ready["ready"] is True
    assert ready["missing_config"] == []


@pytest.mark.asyncio
async def test_is_ready_false_when_llm_missing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai.async")
    p = SkillberryPluginDocGenerator()  # no llm_client set
    ready = await p.is_ready()
    assert ready["ready"] is False


@pytest.mark.asyncio
async def test_is_ready_false_when_required_env_missing(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    p = _make_plugin_with_mock_llm()
    ready = await p.is_ready()
    assert ready["ready"] is False
    assert "LLM_PROVIDER" in ready["missing_config"]


# ── router / UI ──────────────────────────────────────────────────────────────


def test_router_exposes_generate_and_refresh():
    p = _make_plugin_with_mock_llm()
    router = p.get_router()
    paths = {r.path for r in router.routes}
    assert "/generate" in paths
    assert "/refresh" in paths


# ── endpoint validation / gating ─────────────────────────────────────────────


@pytest.mark.skip(reason="TODO: rewrite body-validation test for FastAPI + async router body handling")
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


@pytest.mark.skip(reason="TODO: rewrite endpoint-503 test for FastAPI + async router body handling")
def test_endpoint_returns_503_when_llm_unavailable():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # No LLM client -> not enabled
    plugin = SkillberryPluginDocGenerator()
    plugin._status_message = "LLM unavailable"

    app = FastAPI()
    app.include_router(plugin.get_router())
    client = TestClient(app)
    r = client.post("/generate", json={"object_type": "tool", "uuid": "t1"})
    assert r.status_code == 503


# ── parameter extraction (LLM-independent) ───────────────────────────────────


@pytest.mark.asyncio
async def test_list_parameter_schema_form_supported():
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
    obj = await store.get_tool("t1")
    object_doc = await p._to_object_doc("tool", "t1", obj)
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
    stored = await store.get_tool("t1")
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
    stored = await store.get_snippet("s1")
    block = stored["extra"]["documentation"]
    assert "current" in block and "proposed" not in block
    assert any(t == "doc:status:applied" for t in stored["tags"])


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
    p = SkillberryPluginDocGenerator()
    p._store = FakeStore({("tool", "t1"): {"name": "t"}})
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
    obj = await store.get_tool("t1")
    obj["parameters"] = {
        "properties": {"a": {"type": "string"}, "b": {"type": "int"}},
        "required": ["b"],
    }
    await store.update_tool("t1", obj)

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


@pytest.mark.asyncio
async def test_on_tool_added_auto_proposes_when_enabled():
    store = FakeStore({("tool", "t1"): {"name": "t", "content": "x"}})
    p = _plugin(store)
    await p._on_tool_added(dummy_event("content.tool.added", {"uuid": "t1"}))
    stored = await store.get_tool("t1")
    # Auto-hook proposes (never applies)
    assert stored["extra"]["documentation"].get("proposed")
    assert "current" not in stored["extra"]["documentation"]


@pytest.mark.asyncio
async def test_on_skill_added_auto_proposes():
    store = FakeStore({("skill", "s1"): {"name": "s"}})
    p = _plugin(store)
    await p._on_skill_added(dummy_event("content.skill.added", {"uuid": "s1"}))
    stored = await store.get_skill("s1")
    assert stored["extra"]["documentation"].get("proposed")


@pytest.mark.asyncio
async def test_on_snippet_added_auto_proposes():
    store = FakeStore({("snippet", "n1"): {"name": "n", "content": "z"}})
    p = _plugin(store)
    await p._on_snippet_added(dummy_event("content.snippet.added", {"uuid": "n1"}))
    stored = await store.get_snippet("n1")
    assert stored["extra"]["documentation"].get("proposed")


@pytest.mark.asyncio
async def test_auto_propose_skipped_when_store_not_set():
    # A brand-new plugin without _store: hook must not raise
    p = SkillberryPluginDocGenerator()
    p.llm_client = MagicMock()  # enabled
    await p._on_tool_added(dummy_event("content.tool.added", {"uuid": "any-uuid"}))


@pytest.mark.asyncio
async def test_auto_propose_skipped_when_disabled():
    # LLM not set -> is_enabled() is False -> hook is a no-op
    store = FakeStore({("tool", "t1"): {"name": "t"}})
    p = SkillberryPluginDocGenerator()
    p._store = store
    await p._on_tool_added(dummy_event("content.tool.added", {"uuid": "t1"}))
    stored = await store.get_tool("t1")
    assert "extra" not in stored or "documentation" not in (stored.get("extra") or {})


@pytest.mark.asyncio
async def test_auto_propose_ignores_missing_uuid():
    store = FakeStore()
    p = _plugin(store)
    # Should not raise; nothing to do
    await p._on_tool_added(dummy_event("content.tool.added", {}))
