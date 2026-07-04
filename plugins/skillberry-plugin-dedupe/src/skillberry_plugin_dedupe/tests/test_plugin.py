"""Tests for SkillberryPluginDedupe (SDK-based)."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
from skillberry_plugin_sdk.testing import dummy_event


# ── helpers ──────────────────────────────────────────────────────────────────

def _install_llm(plugin: SkillberryPluginDedupe, *, working: bool = True) -> None:
    """Simulate a completed on_start with a mocked LLM client on the plugin."""
    if working:
        plugin.llm_client = MagicMock()
        plugin._status_message = "Ready (using mock)"
    else:
        plugin.llm_client = None
        plugin._status_message = "LLM unavailable: test"


def _make_plugin_with_mock_llm() -> SkillberryPluginDedupe:
    plugin = SkillberryPluginDedupe()
    _install_llm(plugin, working=True)
    return plugin


def _make_plugin_disabled() -> SkillberryPluginDedupe:
    plugin = SkillberryPluginDedupe()
    _install_llm(plugin, working=False)
    return plugin


def _make_async_store(skills=None):
    """Return an AsyncMock StoreClient prepopulated with helpers used by tests."""
    store = AsyncMock()
    store.list_skills = AsyncMock(return_value=list(skills or []))
    store.get_skill = AsyncMock(return_value=None)
    store.update_skill_tags = AsyncMock(return_value=None)
    store.update_skill = AsyncMock(return_value=None)
    store._request = AsyncMock(return_value=None)
    return store


def _wire(plugin: SkillberryPluginDedupe, store) -> None:
    plugin._store = store


def _make_plugin_in_mode(mode: str) -> SkillberryPluginDedupe:
    with patch.dict(os.environ, {"DEDUPE_MODE": mode}):
        plugin = SkillberryPluginDedupe()
    _install_llm(plugin, working=True)
    return plugin


# ── manifest / config ─────────────────────────────────────────────────────────

def test_plugin_manifest_slug():
    plugin = SkillberryPluginDedupe()
    assert plugin.manifest.slug == "dedupe"


def test_plugin_manifest_type_evaluator():
    plugin = SkillberryPluginDedupe()
    assert plugin.manifest.plugin_type == "evaluator"


def test_plugin_manifest_version():
    plugin = SkillberryPluginDedupe()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_has_api():
    plugin = SkillberryPluginDedupe()
    assert plugin.manifest.has_api is True


def test_plugin_disabled_when_llm_unavailable():
    plugin = _make_plugin_disabled()
    assert not plugin.is_enabled()
    msg = plugin.get_status_message().lower()
    assert "llm" in msg or "unavailable" in msg


def test_plugin_enabled_when_llm_available():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.is_enabled()


def test_plugin_router_is_not_none():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_router() is not None


# ── on_start LLM initialization ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_on_start_initializes_llm_when_available():
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginDedupe()
        await plugin.on_start()
    assert plugin.is_enabled()


@pytest.mark.asyncio
async def test_on_start_handles_missing_llm_switchboard():
    # Force ImportError by removing llm_switchboard from sys.modules and blocking import
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "llm_switchboard":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        plugin = SkillberryPluginDedupe()
        await plugin.on_start()
    assert not plugin.is_enabled()


@pytest.mark.asyncio
async def test_on_start_handles_llm_init_failure():
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("boom")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginDedupe()
        await plugin.on_start()
    assert not plugin.is_enabled()


# ── is_ready ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_is_ready_true_when_llm_available():
    plugin = _make_plugin_with_mock_llm()
    result = await plugin.is_ready()
    assert result["ready"] is True


@pytest.mark.asyncio
async def test_is_ready_false_when_llm_missing():
    plugin = _make_plugin_disabled()
    result = await plugin.is_ready()
    assert result["ready"] is False
    assert "LLM_PROVIDER" in result["missing_config"]


# ── event handler wiring ─────────────────────────────────────────────────────

def test_event_handler_registered_for_skill_added_and_updated():
    from skillberry_plugin_sdk.decorators import get_event_handlers

    plugin = _make_plugin_with_mock_llm()
    handlers = get_event_handlers(plugin)
    assert "content.skill.added" in handlers
    assert "content.skill.updated" in handlers


def test_no_event_handlers_for_tools_or_snippets():
    from skillberry_plugin_sdk.decorators import get_event_handlers

    plugin = _make_plugin_with_mock_llm()
    handlers = get_event_handlers(plugin)
    for topic in handlers:
        assert "tool" not in topic
        assert "snippet" not in topic


@pytest.mark.asyncio
async def test_on_skill_change_dispatches_check_for_duplicates():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    _wire(plugin, store)
    with patch.object(plugin, "_check_for_duplicates", new=AsyncMock()) as mock_check:
        await plugin.on_skill_change(dummy_event("content.skill.added", {"uuid": "s-1"}))
        mock_check.assert_awaited_once_with("s-1")


@pytest.mark.asyncio
async def test_on_skill_change_ignores_missing_uuid():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    _wire(plugin, store)
    with patch.object(plugin, "_check_for_duplicates", new=AsyncMock()) as mock_check:
        await plugin.on_skill_change(dummy_event("content.skill.added", {}))
        mock_check.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_skill_change_skipped_when_plugin_disabled():
    plugin = _make_plugin_disabled()
    store = _make_async_store()
    _wire(plugin, store)
    with patch.object(plugin, "_check_for_duplicates", new=AsyncMock()) as mock_check:
        await plugin.on_skill_change(dummy_event("content.skill.added", {"uuid": "s-1"}))
        mock_check.assert_not_awaited()


# ── _get_candidate_skills ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_candidate_skills_excludes_trigger_skill():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store(skills=[
        {"uuid": "s-trigger", "name": "trigger", "description": "d", "tags": []},
        {"uuid": "s-other", "name": "other", "description": "d", "tags": []},
    ])
    _wire(plugin, store)
    candidates = await plugin._get_candidate_skills("s-trigger")
    uuids = [c["uuid"] for c in candidates]
    assert "s-trigger" not in uuids
    assert "s-other" in uuids


@pytest.mark.asyncio
async def test_get_candidate_skills_excludes_skills_tagged_as_duplicates():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store(skills=[
        {"uuid": "s-orig", "name": "original", "description": "d", "tags": []},
        {"uuid": "s-dup", "name": "dup", "description": "d", "tags": ["duplicate:original"]},
    ])
    _wire(plugin, store)
    candidates = await plugin._get_candidate_skills("s-new")
    uuids = [c["uuid"] for c in candidates]
    assert "s-orig" in uuids
    assert "s-dup" not in uuids


@pytest.mark.asyncio
async def test_get_candidate_skills_returns_empty_when_only_trigger_exists():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store(skills=[
        {"uuid": "s-1", "name": "only", "description": "d", "tags": []},
    ])
    _wire(plugin, store)
    assert await plugin._get_candidate_skills("s-1") == []


@pytest.mark.asyncio
async def test_get_candidate_skills_returns_empty_when_all_are_duplicates():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store(skills=[
        {"uuid": "s-dup1", "tags": ["duplicate:x"]},
        {"uuid": "s-dup2", "tags": ["duplicate:y", "python"]},
    ])
    _wire(plugin, store)
    assert await plugin._get_candidate_skills("s-new") == []


# ── _build_prompt ────────────────────────────────────────────────────────────

def test_build_prompt_contains_trigger_skill_name_and_description():
    plugin = _make_plugin_with_mock_llm()
    skill = {"name": "my_skill", "description": "searches the web for results"}
    candidates = [{"name": "other", "description": "does something else"}]
    prompt = plugin._build_prompt(skill, candidates)
    assert "my_skill" in prompt
    assert "searches the web for results" in prompt


def test_build_prompt_contains_all_candidates():
    plugin = _make_plugin_with_mock_llm()
    skill = {"name": "new", "description": "desc"}
    candidates = [
        {"name": "cand-a", "description": "alpha desc"},
        {"name": "cand-b", "description": "beta desc"},
    ]
    prompt = plugin._build_prompt(skill, candidates)
    assert "cand-a" in prompt
    assert "alpha desc" in prompt
    assert "cand-b" in prompt
    assert "beta desc" in prompt


def test_build_prompt_requests_json_array_output():
    plugin = _make_plugin_with_mock_llm()
    prompt = plugin._build_prompt(
        {"name": "x", "description": "y"},
        [{"name": "z", "description": "w"}],
    )
    assert "JSON" in prompt or "json" in prompt
    assert "[]" in prompt or "empty" in prompt.lower()


# ── _parse_llm_response ──────────────────────────────────────────────────────

def test_parse_llm_response_valid_json_with_duplicates():
    plugin = _make_plugin_with_mock_llm()
    response = '[{"name": "skill-a", "reason": "very similar description"}]'
    findings = plugin._parse_llm_response(response)
    assert len(findings) == 1
    assert findings[0]["name"] == "skill-a"
    assert findings[0]["reason"] == "very similar description"


def test_parse_llm_response_empty_array():
    plugin = _make_plugin_with_mock_llm()
    findings = plugin._parse_llm_response("[]")
    assert findings == []


def test_parse_llm_response_tolerates_surrounding_prose():
    plugin = _make_plugin_with_mock_llm()
    response = 'Sure, here are the duplicates:\n[{"name": "x", "reason": "same thing"}]\nDone.'
    findings = plugin._parse_llm_response(response)
    assert len(findings) == 1
    assert findings[0]["name"] == "x"


def test_parse_llm_response_multiple_duplicates():
    plugin = _make_plugin_with_mock_llm()
    response = '[{"name": "a", "reason": "r1"}, {"name": "b", "reason": "r2"}]'
    findings = plugin._parse_llm_response(response)
    assert len(findings) == 2
    names = {f["name"] for f in findings}
    assert names == {"a", "b"}


def test_parse_llm_response_raises_on_no_json_array():
    plugin = _make_plugin_with_mock_llm()
    with pytest.raises(ValueError, match="No JSON array"):
        plugin._parse_llm_response("No duplicates found.")


def test_parse_llm_response_skips_entries_missing_name_or_reason():
    plugin = _make_plugin_with_mock_llm()
    response = '[{"name": "ok", "reason": "good"}, {"only_name": "bad"}]'
    findings = plugin._parse_llm_response(response)
    assert len(findings) == 1
    assert findings[0]["name"] == "ok"


# ── _apply_duplicate_findings ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_duplicate_findings_writes_tags():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store.get_skill = AsyncMock(return_value={"uuid": "s-1", "extra": {}, "tags": []})
    _wire(plugin, store)

    await plugin._apply_duplicate_findings("s-1", [{"name": "skill-x", "reason": "same"}])

    store.update_skill_tags.assert_awaited_once_with("s-1", ["duplicate:skill-x"])


@pytest.mark.asyncio
async def test_apply_duplicate_findings_writes_duplicate_analysis_to_extra():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store.get_skill = AsyncMock(return_value={"uuid": "s-1", "extra": {}, "tags": []})
    _wire(plugin, store)

    await plugin._apply_duplicate_findings("s-1", [{"name": "skill-x", "reason": "same thing"}])

    store.update_skill.assert_awaited_once()
    written = store.update_skill.call_args[0][1]
    assert written["extra"]["duplicate_analysis"] == {"skill-x": "same thing"}


@pytest.mark.asyncio
async def test_apply_duplicate_findings_preserves_existing_analysis():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store.get_skill = AsyncMock(return_value={
        "uuid": "s-1",
        "extra": {"duplicate_analysis": {"skill-old": "old reason"}},
        "tags": [],
    })
    _wire(plugin, store)

    await plugin._apply_duplicate_findings("s-1", [{"name": "skill-new", "reason": "new reason"}])

    written = store.update_skill.call_args[0][1]
    analysis = written["extra"]["duplicate_analysis"]
    assert analysis["skill-old"] == "old reason"
    assert analysis["skill-new"] == "new reason"


@pytest.mark.asyncio
async def test_apply_duplicate_findings_multiple_findings():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store.get_skill = AsyncMock(return_value={"uuid": "s-1", "extra": {}, "tags": []})
    _wire(plugin, store)

    findings = [
        {"name": "skill-a", "reason": "reason a"},
        {"name": "skill-b", "reason": "reason b"},
    ]
    await plugin._apply_duplicate_findings("s-1", findings)

    store.update_skill_tags.assert_awaited_once_with(
        "s-1", ["duplicate:skill-a", "duplicate:skill-b"]
    )
    written = store.update_skill.call_args[0][1]
    analysis = written["extra"]["duplicate_analysis"]
    assert analysis["skill-a"] == "reason a"
    assert analysis["skill-b"] == "reason b"


@pytest.mark.asyncio
async def test_apply_duplicate_findings_no_op_when_empty():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    _wire(plugin, store)

    await plugin._apply_duplicate_findings("s-1", [])

    store.update_skill_tags.assert_not_awaited()
    store.update_skill.assert_not_awaited()


# ── _check_for_duplicates ────────────────────────────────────────────────────

def _skill(uuid, name, description, tags=None):
    return {"uuid": uuid, "name": name, "description": description, "tags": tags or [], "extra": {}}


@pytest.mark.asyncio
async def test_check_for_duplicates_skips_when_skill_not_found():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store.get_skill = AsyncMock(return_value=None)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock()

    await plugin._check_for_duplicates("missing-uuid")

    plugin.llm_client.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_skips_when_description_too_short():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store.get_skill = AsyncMock(return_value=_skill("s-1", "x", "short"))
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock()

    await plugin._check_for_duplicates("s-1")

    plugin.llm_client.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_skips_when_no_candidates():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-1", "only skill", "this is a sufficiently long description here")
    store = _make_async_store(skills=[trigger])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock()

    await plugin._check_for_duplicates("s-1")

    plugin.llm_client.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_no_op_when_llm_returns_empty_array():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "skill", "a sufficiently long description for testing")
    candidate = _skill("s-old", "other", "completely different capability for testing")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value="[]")

    await plugin._check_for_duplicates("s-new")

    store.update_skill_tags.assert_not_awaited()
    store.update_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_for_duplicates_tags_skill_when_duplicate_found():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "search tool", "performs web searches and returns ranked results")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(
        return_value='[{"name": "search tool", "reason": "Both describe web search with ranked results"}]'
    )

    await plugin._check_for_duplicates("s-new")

    store.update_skill_tags.assert_awaited_once_with("s-new", ["duplicate:search tool"])


@pytest.mark.asyncio
async def test_check_for_duplicates_multiple_duplicates_all_tagged():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "searcher", "searches the web and returns ranked results for any query")
    cand_a = _skill("s-a", "web search", "queries web and returns ranked results for a given input")
    cand_b = _skill("s-b", "search api", "performs web queries returning relevance-ranked results")
    store = _make_async_store(skills=[trigger, cand_a, cand_b])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(
        return_value='[{"name": "web search", "reason": "same"}, {"name": "search api", "reason": "same"}]'
    )

    await plugin._check_for_duplicates("s-new")

    call_tags = store.update_skill_tags.call_args[0][1]
    assert "duplicate:web search" in call_tags
    assert "duplicate:search api" in call_tags


@pytest.mark.asyncio
async def test_check_for_duplicates_logs_error_on_llm_failure():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "skill", "a sufficiently long description for testing purposes")
    candidate = _skill("s-old", "other", "another sufficiently long description for comparison")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(side_effect=RuntimeError("API error"))

    await plugin._check_for_duplicates("s-new")  # must not raise

    store.update_skill_tags.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_for_duplicates_logs_error_on_parse_failure():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "skill", "a sufficiently long description for testing purposes")
    candidate = _skill("s-old", "other", "another sufficiently long description for comparison")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value="not valid json at all")

    await plugin._check_for_duplicates("s-new")  # must not raise

    store.update_skill_tags.assert_not_awaited()


# ── DEDUPE_MODE ──────────────────────────────────────────────────────────────

def test_plugin_defaults_to_interactive_mode():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DEDUPE_MODE", None)
        plugin = _make_plugin_with_mock_llm()
    assert plugin._mode == "interactive"


def test_plugin_uses_non_blocking_mode_when_env_set():
    plugin = _make_plugin_in_mode("non_blocking")
    assert plugin._mode == "non_blocking"


def test_plugin_has_pending_decisions_dict():
    plugin = _make_plugin_with_mock_llm()
    assert isinstance(plugin._pending_decisions, dict)
    assert len(plugin._pending_decisions) == 0


# ── _check_for_duplicates — interactive vs non_blocking ──────────────────────

@pytest.mark.asyncio
async def test_check_for_duplicates_creates_pending_decision_in_interactive_mode():
    plugin = _make_plugin_in_mode("interactive")
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "search tool", "performs web searches and returns ranked results")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(
        return_value='[{"name": "search tool", "reason": "Both describe web search"}]'
    )

    await plugin._check_for_duplicates("s-new")

    assert "s-new" in plugin._pending_decisions
    decision = plugin._pending_decisions["s-new"]
    assert decision["uuid"] == "s-new"
    assert decision["skill_name"] == "web searcher"
    assert len(decision["duplicates"]) == 1
    assert decision["duplicates"][0]["name"] == "search tool"
    assert "detected_at" in decision


@pytest.mark.asyncio
async def test_check_for_duplicates_does_not_create_pending_decision_in_non_blocking_mode():
    plugin = _make_plugin_in_mode("non_blocking")
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "search tool", "performs web searches and returns ranked results")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(
        return_value='[{"name": "search tool", "reason": "Both describe web search"}]'
    )

    await plugin._check_for_duplicates("s-new")

    assert "s-new" not in plugin._pending_decisions


@pytest.mark.asyncio
async def test_check_for_duplicates_tags_skill_in_both_modes():
    for mode in ("interactive", "non_blocking"):
        plugin = _make_plugin_in_mode(mode)
        trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
        candidate = _skill("s-old", "search tool", "performs web searches and returns ranked results")
        store = _make_async_store(skills=[trigger, candidate])
        store.get_skill = AsyncMock(return_value=trigger)
        _wire(plugin, store)
        plugin.llm_client.generate_async = AsyncMock(
            return_value='[{"name": "search tool", "reason": "Both describe web search"}]'
        )

        await plugin._check_for_duplicates("s-new")

        store.update_skill_tags.assert_awaited_with("s-new", ["duplicate:search tool"])


@pytest.mark.asyncio
async def test_check_for_duplicates_no_pending_decision_when_no_duplicates_found():
    plugin = _make_plugin_in_mode("interactive")
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "other skill", "completely unrelated capability for managing files")
    store = _make_async_store(skills=[trigger, candidate])
    store.get_skill = AsyncMock(return_value=trigger)
    _wire(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value="[]")

    await plugin._check_for_duplicates("s-new")

    assert "s-new" not in plugin._pending_decisions


# ── HTTP router ──────────────────────────────────────────────────────────────

def _make_router_client(plugin) -> TestClient:
    app = FastAPI()
    router = plugin.get_router()
    app.include_router(router)
    return TestClient(app)


def test_get_decisions_returns_empty_list_when_none_pending():
    plugin = _make_plugin_with_mock_llm()
    client = _make_router_client(plugin)
    response = client.get("/decisions")
    assert response.status_code == 200
    assert response.json() == []


def test_get_decisions_returns_pending_decisions():
    plugin = _make_plugin_with_mock_llm()
    plugin._pending_decisions["s-1"] = {
        "uuid": "s-1",
        "skill_name": "My Skill",
        "duplicates": [{"name": "other", "reason": "same"}],
        "detected_at": "2026-06-18T10:00:00Z",
    }
    client = _make_router_client(plugin)
    response = client.get("/decisions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["uuid"] == "s-1"
    assert data[0]["skill_name"] == "My Skill"


def test_keep_decision_removes_it_from_pending():
    plugin = _make_plugin_with_mock_llm()
    plugin._pending_decisions["s-1"] = {
        "uuid": "s-1",
        "skill_name": "My Skill",
        "duplicates": [],
        "detected_at": "2026-06-18T10:00:00Z",
    }
    client = _make_router_client(plugin)
    response = client.post("/decisions/s-1/keep")
    assert response.status_code == 200
    assert "s-1" not in plugin._pending_decisions
    assert "kept" in response.json()["message"].lower()


def test_keep_decision_returns_404_for_unknown_uuid():
    plugin = _make_plugin_with_mock_llm()
    client = _make_router_client(plugin)
    response = client.post("/decisions/nonexistent/keep")
    assert response.status_code == 404


def test_delete_decision_calls_store_delete_and_removes_pending():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    _wire(plugin, store)
    plugin._pending_decisions["s-2"] = {
        "uuid": "s-2",
        "skill_name": "Duplicate Skill",
        "duplicates": [],
        "detected_at": "2026-06-18T10:00:00Z",
    }
    client = _make_router_client(plugin)
    response = client.post("/decisions/s-2/delete")
    assert response.status_code == 200
    store._request.assert_awaited_once_with("DELETE", "/skills/s-2")
    assert "s-2" not in plugin._pending_decisions
    assert "deleted" in response.json()["message"].lower()


def test_delete_decision_returns_404_for_unknown_uuid():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    _wire(plugin, store)
    client = _make_router_client(plugin)
    response = client.post("/decisions/nonexistent/delete")
    assert response.status_code == 404


def test_delete_decision_removes_pending_even_when_store_delete_fails():
    plugin = _make_plugin_with_mock_llm()
    store = _make_async_store()
    store._request = AsyncMock(side_effect=RuntimeError("boom"))
    _wire(plugin, store)
    plugin._pending_decisions["s-3"] = {
        "uuid": "s-3",
        "skill_name": "Some Skill",
        "duplicates": [],
        "detected_at": "2026-06-18T10:00:00Z",
    }
    client = _make_router_client(plugin)
    response = client.post("/decisions/s-3/delete")
    assert response.status_code == 200
    assert "s-3" not in plugin._pending_decisions


# ── UI config (via manifest) ─────────────────────────────────────────────────

def test_manifest_can_carry_ui_config():
    """UI config now lives in the manifest (optional); dedupe doesn't set it."""
    plugin = SkillberryPluginDedupe()
    # ui_config is optional in the manifest schema — just verify it's readable.
    assert plugin.manifest.ui_config in (None, {}) or isinstance(plugin.manifest.ui_config, dict)
