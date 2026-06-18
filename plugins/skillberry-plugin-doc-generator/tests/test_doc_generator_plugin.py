"""Tests for the doc-generator plugin (mocked store, no network/LLM)."""

import copy

import pytest

from skillberry_plugin_doc_generator.plugin import SkillberryPluginDocGenerator
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


def _plugin(store):
    p = SkillberryPluginDocGenerator()
    p.set_store_api(store)
    return p


def test_metadata_and_enablement():
    p = SkillberryPluginDocGenerator()
    assert p.metadata.name == "Documentation Generator"
    assert p.metadata.plugin_type == PluginType.EVALUATOR
    assert p.is_enabled() is True
    assert "backend" in p.get_status_message()


def test_router_exposes_generate_and_refresh():
    p = SkillberryPluginDocGenerator()
    router = p.get_router()
    paths = {r.path for r in router.routes}
    assert "/generate" in paths
    assert "/refresh" in paths


def test_ui_config_actions():
    p = SkillberryPluginDocGenerator()
    cfg = p.get_ui_config()
    labels = {a["label"] for a in cfg["actions"]}
    assert any("Generate" in l for l in labels)
    assert any("Refresh" in l for l in labels)
    # object_type must carry a default so the generic UI form pre-populates it.
    for action in cfg["actions"]:
        ot = action["params_schema"]["properties"]["object_type"]
        assert ot.get("default") == "tool"


def test_endpoint_validates_blank_and_bad_input_as_400_not_422():
    """The generic UI form may omit the enum field; we want a clean 400."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(SkillberryPluginDocGenerator().get_router())
    client = TestClient(app)

    # empty body: object_type defaults to 'tool', uuid missing -> 400 (not 422)
    r = client.post("/generate", json={})
    assert r.status_code == 400
    assert "uuid is required" in r.json()["detail"]

    # invalid object_type -> 400 with a helpful message
    r = client.post("/generate", json={"object_type": "widget", "uuid": "x"})
    assert r.status_code == 400
    assert "object_type must be one of" in r.json()["detail"]


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
    assert doc["backend"] == "heuristic"
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
    # refreshed docs proposed (not applied) and reflect the new params
    assert r2["applied"] is False
    assert any(pp["name"] == "b" for pp in r2["documentation"]["parameters"])


@pytest.mark.asyncio
async def test_enrich_preserves_thin_author_description():
    store = FakeStore(
        {
            ("tool", "t1"): {
                "name": "fetch",
                "description": "Gets data",  # thin
                "content": "import requests",
            }
        }
    )
    p = _plugin(store)
    result = await p.generate_docs("tool", "t1", apply=True)
    desc = result["documentation"]["description"]
    assert desc.startswith("Gets data")  # author words preserved
    assert result["documentation"]["mode"] == "enriched"


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
    result = await p.generate_docs("tool", "t1")
    params = result["documentation"]["parameters"]
    assert params[0]["name"] == "x"
    assert params[0]["description"] == "the x"  # author param doc preserved
