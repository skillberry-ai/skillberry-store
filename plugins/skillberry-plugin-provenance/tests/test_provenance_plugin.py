"""Tests for the provenance plugin (fake source + AsyncMock store, no network)."""

import contextlib
from unittest.mock import AsyncMock, patch

import pytest

from skillberry_plugin_provenance.plugin import (
    SkillberryPluginProvenance,
    _compute_drift,
)
from skillberry_plugin_provenance.sources.base import Background
from skillberry_plugin_sdk.testing import dummy_event

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


def _mock_store(skill=None, tool=None, tool_module=None, snippet=None):
    """Build an AsyncMock StoreClient wired for provenance's access patterns."""
    store = AsyncMock()
    store.get_skill = AsyncMock(return_value=skill)
    store.get_tool = AsyncMock(return_value=tool)
    store.get_snippet = AsyncMock(return_value=snippet)
    store.update_skill = AsyncMock(return_value={"success": True})

    async def _get(path, params=None):
        if path.startswith("/tools/") and path.endswith("/module"):
            return tool_module
        return None

    store.get = AsyncMock(side_effect=_get)
    return store


def _plugin_with_store(**kwargs):
    """Helper: yields a plugin instance with `_store` attached."""
    cm = _make_plugin(source=kwargs.pop("source", None))
    plugin = cm.__enter__()
    store = _mock_store(**kwargs)
    plugin._store = store
    return cm, plugin, store


# ── manifest ─────────────────────────────────────────────────────────────────


def test_plugin_manifest_slug():
    with _make_plugin() as plugin:
        assert plugin.manifest.slug == "provenance"


def test_plugin_manifest_type_evaluator():
    with _make_plugin() as plugin:
        assert plugin.manifest.plugin_type == "evaluator"


def test_plugin_manifest_has_api():
    with _make_plugin() as plugin:
        assert plugin.manifest.has_api is True


# ── gather: pre-import (url) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gather_pre_import_url_no_store():
    with _make_plugin() as plugin:
        # No uuid → behavior degrades to unavailable and no store methods hit.
        plugin._store = _mock_store()
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
    cm, plugin, store = _plugin_with_store(skill=skill)
    try:
        data = await plugin.gather_background(uuid="s1", persist_baseline=True)
    finally:
        cm.__exit__(None, None, None)

    assert data["confidence"] == "high"
    # persisted into extra["provenance"].baseline + latest via update_skill
    store.update_skill.assert_awaited()
    written = store.update_skill.call_args[0][1]
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
    cm, plugin, store = _plugin_with_store(skill=skill)
    try:
        with pytest.raises(ValueError):
            await plugin.gather_background(uuid="s2")
    finally:
        cm.__exit__(None, None, None)


# ── behavior section over child code ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_behavior_detects_domains_and_ops():
    skill = {
        "uuid": "s3", "name": "x", "tags": [],
        "extra": {"origin": {"type": "github", "url": "https://github.com/a/b"},
                  "evaluation": {"sast": {"summary": {"high": 1}}}},
        "tool_uuids": ["t1"], "snippet_uuids": [],
    }
    tool = {"uuid": "t1", "name": "t", "module_name": "tool.py"}
    tool_module = (
        "import requests\nrequests.get('https://evil.example.com/x')\n"
        "import subprocess\nsubprocess.run(['ls'])\n"
    )
    cm, plugin, store = _plugin_with_store(
        skill=skill, tool=tool, tool_module=tool_module
    )
    try:
        data = await plugin.gather_background(uuid="s3")
    finally:
        cm.__exit__(None, None, None)

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
    cm, plugin, store = _plugin_with_store(source=_FakeSource(bg=bg), skill=skill)
    try:
        out = await plugin.recheck("s4")
    finally:
        cm.__exit__(None, None, None)
    assert out["drift"] == []


# ── router (TestClient) ──────────────────────────────────────────────────────


def _client(plugin):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(plugin.get_router())
    return TestClient(app)


def test_router_check_with_url_200():
    with _make_plugin() as plugin:
        plugin._store = _mock_store()
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
    with _make_plugin() as plugin:
        plugin._store = _mock_store(skill=None)
        resp = _client(plugin).post(
            "/plugins/provenance/check", json={"uuid": "missing"}
        )
        assert resp.status_code == 404


def test_router_check_no_args_404():
    with _make_plugin() as plugin:
        plugin._store = _mock_store()
        resp = _client(plugin).post("/plugins/provenance/check", json={})
        assert resp.status_code == 404


# ── event handler dispatch ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_skill_added_triggers_baseline_when_origin_present():
    skill = {
        "uuid": "s5", "name": "x", "tags": [],
        "extra": {"origin": {"type": "github", "url": "https://github.com/a/b"}},
        "tool_uuids": [], "snippet_uuids": [],
    }
    cm, plugin, store = _plugin_with_store(skill=skill)
    try:
        await plugin.on_skill_added(dummy_event("content.skill.added", {"uuid": "s5"}))
    finally:
        cm.__exit__(None, None, None)
    # baseline was persisted → update_skill called at least once with prov data
    store.update_skill.assert_awaited()
    written = store.update_skill.call_args[0][1]
    assert "baseline" in written["extra"]["provenance"]


@pytest.mark.asyncio
async def test_on_skill_added_ignores_skills_without_origin():
    skill = {"uuid": "s6", "name": "x", "tags": [], "extra": {}}
    cm, plugin, store = _plugin_with_store(skill=skill)
    try:
        await plugin.on_skill_added(dummy_event("content.skill.added", {"uuid": "s6"}))
    finally:
        cm.__exit__(None, None, None)
    # nothing persisted — origin missing means no baseline attempt
    store.update_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_skill_added_ignores_missing_uuid():
    cm, plugin, store = _plugin_with_store(skill=None)
    try:
        await plugin.on_skill_added(dummy_event("content.skill.added", {}))
    finally:
        cm.__exit__(None, None, None)
    store.get_skill.assert_not_awaited()
