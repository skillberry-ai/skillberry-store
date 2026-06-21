"""Tests for the provenance plugin (fake source + mocked store, no network)."""

import contextlib
from unittest.mock import MagicMock, patch

import pytest

from skillberry_plugin_provenance.plugin import (
    SkillberryPluginProvenance,
    _compute_drift,
)
from skillberry_plugin_provenance.sources.base import Background
from skillberry_store.plugins.base import PluginType

# ── a fake source so the plugin never hits the network ───────────────────────


def _fake_background(confidence="high", spdx="MIT", verified=True):
    bg = Background(source="github")
    bg.provenance = {"status": "ok", "commit_sha": "sha1", "owner": "anthropics"}
    bg.publisher = {"status": "ok", "owner": "anthropics", "stars": 4200,
                    "owner_type": "Organization", "archived": False}
    bg.license = {"status": "ok", "spdx_id": spdx, "category": "permissive"}
    bg.integrity = {"status": "ok", "commit_verified": verified}
    bg.confidence = confidence
    return bg


class _FakeSource:
    name = "github"

    def __init__(self, bg=None):
        self._bg = bg or _fake_background()

    def matches(self, origin):
        return True

    def gather(self, origin):
        return self._bg


@contextlib.contextmanager
def _make_plugin(source=None):
    """Yield a plugin with resolve_source patched to a fake source."""
    src = source or _FakeSource()
    with patch(
        "skillberry_plugin_provenance.plugin.resolve_source",
        lambda origin: src,
    ):
        yield SkillberryPluginProvenance()


def _mock_store(skill=None):
    store = MagicMock()
    store.get_skill.return_value = skill
    store.get_tool.return_value = None
    store.get_snippet.return_value = None
    store.skills = MagicMock()
    store.skills.write_dict.return_value = {"success": True}
    store.tools = MagicMock()
    return store


# ── metadata / enablement ────────────────────────────────────────────────────


def test_metadata():
    with _make_plugin() as plugin:
        md = plugin.metadata
        assert md.name == "Skill Provenance & Background"
        assert md.plugin_type == PluginType.EVALUATOR
        assert plugin.is_enabled() is True


# ── gather: pre-import (url) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gather_pre_import_url_no_store():
    with _make_plugin() as plugin:
        # no store needed for a pure url check; behavior degrades to unavailable
        data = await plugin.gather_background(url="https://github.com/anthropics/skills")
        assert data["confidence"] == "high"
        assert data["license"]["spdx_id"] == "MIT"
        assert data["behavior"]["status"] == "unavailable"


# ── gather: post-import (uuid) reads origin + persists baseline ──────────────


@pytest.mark.asyncio
async def test_gather_post_import_persists_baseline_and_tags():
    skill = {
        "uuid": "s1",
        "name": "pptx",
        "tags": ["anthropic", "imported"],
        "extra": {"origin": {"type": "github", "url": "https://github.com/anthropics/skills"}},
        "tool_uuids": [],
        "snippet_uuids": [],
    }
    store = _mock_store(skill=skill)
    with _make_plugin() as plugin:
        plugin.set_store_api(store)
        data = await plugin.gather_background(uuid="s1", persist_baseline=True)

    assert data["confidence"] == "high"
    # persisted into extra["provenance"].baseline + latest
    written = store.skills.write_dict.call_args[0][1]
    assert written["extra"]["provenance"]["baseline"]["confidence"] == "high"
    assert written["extra"]["provenance"]["latest"]["confidence"] == "high"
    # roll-up tags added, old provenance tags would be stripped
    assert "provenance:confidence:high" in written["tags"]
    assert "provenance:license:MIT" in written["tags"]
    assert "provenance:verified" in written["tags"]
    # original tags preserved
    assert "anthropic" in written["tags"]


@pytest.mark.asyncio
async def test_gather_uuid_without_origin_raises_valueerror():
    skill = {"uuid": "s2", "name": "x", "tags": [], "extra": {}}
    store = _mock_store(skill=skill)
    with _make_plugin() as plugin:
        plugin.set_store_api(store)
        with pytest.raises(ValueError):
            await plugin.gather_background(uuid="s2")


# ── behavior section over child code ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_behavior_detects_domains_and_ops():
    skill = {
        "uuid": "s3", "name": "x", "tags": [],
        "extra": {"origin": {"type": "github", "url": "https://github.com/a/b"},
                  "evaluation": {"sast": {"summary": {"high": 1}}}},
        "tool_uuids": ["t1"], "snippet_uuids": [],
    }
    store = _mock_store(skill=skill)
    store.get_tool.return_value = {"uuid": "t1", "name": "t", "module_name": "tool.py"}
    store.tools.read_file.return_value = (
        "import requests\nrequests.get('https://evil.example.com/x')\n"
        "import subprocess\nsubprocess.run(['ls'])\n"
    )
    with _make_plugin() as plugin:
        plugin.set_store_api(store)
        data = await plugin.gather_background(uuid="s3")

    beh = data["behavior"]
    assert beh["status"] == "ok"
    assert beh["external_domains"] == ["evil.example.com"]
    assert "network" in beh["sensitive_operations"]
    assert "subprocess" in beh["sensitive_operations"]
    assert beh["sast_summary"] == {"high": 1}
    # integrity gains a per-file content hash
    assert "content_sha256" in data["integrity"]


# ── drift ────────────────────────────────────────────────────────────────────


def test_compute_drift_none_baseline_is_empty():
    assert _compute_drift(None, {"provenance": {}}) == []


def test_compute_drift_detects_commit_license_content():
    baseline = {
        "provenance": {"commit_sha": "old"},
        "license": {"spdx_id": "MIT"},
        "publisher": {"archived": False},
        "integrity": {"content_sha256": {"tool:t": "h1"}},
    }
    current = {
        "provenance": {"commit_sha": "new"},
        "license": {"spdx_id": None},
        "publisher": {"archived": True},
        "integrity": {"content_sha256": {"tool:t": "h2"}},
    }
    drift = _compute_drift(baseline, current)
    assert any("commit changed" in d for d in drift)
    assert any("license changed" in d for d in drift)
    assert any("archived changed" in d for d in drift)
    assert any("content changed" in d for d in drift)


@pytest.mark.asyncio
async def test_recheck_reports_no_drift_against_matching_baseline():
    bg = _fake_background()
    baseline = bg.to_dict()
    # give the stored skill a matching baseline (and an origin)
    skill = {
        "uuid": "s4", "name": "x", "tags": [],
        "extra": {
            "origin": {"type": "github", "url": "https://github.com/a/b"},
            "provenance": {"baseline": baseline},
        },
        "tool_uuids": [], "snippet_uuids": [],
    }
    store = _mock_store(skill=skill)
    with _make_plugin(source=_FakeSource(bg=bg)) as plugin:
        plugin.set_store_api(store)
        out = await plugin.recheck("s4")
    assert out["drift"] == []


# ── router (TestClient) ──────────────────────────────────────────────────────


def _client(plugin):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/provenance")
    return TestClient(app)


def test_router_check_with_url_200():
    with _make_plugin() as plugin:
        resp = _client(plugin).post(
            "/plugins/provenance/check",
            json={"github_url": "https://github.com/anthropics/skills"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["confidence"] == "high"
        assert "Confidence: HIGH" in body["message"]


def test_router_check_unknown_uuid_404():
    store = _mock_store(skill=None)
    with _make_plugin() as plugin:
        plugin.set_store_api(store)
        resp = _client(plugin).post(
            "/plugins/provenance/check", json={"uuid": "missing"}
        )
        assert resp.status_code == 404


def test_router_check_no_args_404():
    with _make_plugin() as plugin:
        resp = _client(plugin).post("/plugins/provenance/check", json={})
        assert resp.status_code == 404


# ── event handler registration ───────────────────────────────────────────────


def test_event_handler_registered_for_skill_add():
    from skillberry_store.plugins import events as events_module

    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        with _make_plugin():
            assert len(events_module._event_handlers.get("content_added:skill", [])) > 0
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)
