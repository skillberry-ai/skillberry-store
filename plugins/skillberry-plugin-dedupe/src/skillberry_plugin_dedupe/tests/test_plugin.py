"""Tests for SkillberryPluginDedupe."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from skillberry_store.plugins.base import PluginType


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_plugin_with_mock_llm():
    """Return a plugin instance with a mocked LLM client."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
        plugin = SkillberryPluginDedupe()
    return plugin


def _make_plugin_disabled():
    """Return a plugin instance where LLM is unavailable."""
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
        plugin = SkillberryPluginDedupe()
    return plugin


def _make_mock_store(skills=None):
    mock_store = MagicMock()
    mock_store.list_skills.return_value = skills or []
    mock_store.get_skill.return_value = None
    mock_store.update_skill_tags.return_value = True
    mock_store.update_skill_metadata.return_value = True
    return mock_store


# ── metadata ─────────────────────────────────────────────────────────────────

def test_plugin_metadata_name_and_type():
    from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
    plugin = SkillberryPluginDedupe()
    assert plugin.metadata.name == "Skill Deduplicator"
    assert plugin.metadata.plugin_type == PluginType.EVALUATOR
    assert plugin.metadata.version == "0.1.0"


def test_plugin_disabled_when_llm_unavailable():
    plugin = _make_plugin_disabled()
    assert not plugin.is_enabled()
    assert "llm" in plugin.get_status_message().lower() or "unavailable" in plugin.get_status_message().lower()


def test_plugin_enabled_when_llm_available():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.is_enabled()


def test_plugin_router_is_not_none():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_router() is not None


def test_plugin_no_cli_commands():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_cli_commands() is None


def test_plugin_ui_config_has_notifications():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_ui_config() is not None
    assert "notifications" in plugin.get_ui_config()


# ── event handler registration ────────────────────────────────────────────────

def test_event_handlers_registered_for_skill_added_and_updated():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        plugin = _make_plugin_with_mock_llm()
        assert len(events_module._event_handlers.get("content_added:skill", [])) > 0
        assert len(events_module._event_handlers.get("content_updated:skill", [])) > 0
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


def test_event_handlers_not_registered_for_tools_or_snippets():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        _make_plugin_with_mock_llm()
        assert "content_added:tool" not in events_module._event_handlers
        assert "content_added:snippet" not in events_module._event_handlers
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_event_handler_skipped_when_plugin_disabled():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        plugin = _make_plugin_disabled()
        plugin.set_store_api(_make_mock_store())
        handler = events_module._event_handlers.get("content_added:skill", [None])[0]
        if handler:
            await handler(uuid="any-uuid")  # must not raise
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_event_handler_skipped_when_store_not_set():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        _make_plugin_with_mock_llm()
        handler = events_module._event_handlers["content_added:skill"][0]
        await handler(uuid="any-uuid")  # must not raise — store not injected
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


# ── _get_candidate_skills ─────────────────────────────────────────────────────

def test_get_candidate_skills_excludes_trigger_skill():
    plugin = _make_plugin_with_mock_llm()
    plugin.set_store_api(_make_mock_store(skills=[
        {"uuid": "s-trigger", "name": "trigger", "description": "d", "tags": []},
        {"uuid": "s-other", "name": "other", "description": "d", "tags": []},
    ]))
    candidates = plugin._get_candidate_skills("s-trigger")
    uuids = [c["uuid"] for c in candidates]
    assert "s-trigger" not in uuids
    assert "s-other" in uuids


def test_get_candidate_skills_excludes_skills_tagged_as_duplicates():
    plugin = _make_plugin_with_mock_llm()
    plugin.set_store_api(_make_mock_store(skills=[
        {"uuid": "s-orig", "name": "original", "description": "d", "tags": []},
        {"uuid": "s-dup", "name": "dup", "description": "d", "tags": ["duplicate:original"]},
    ]))
    candidates = plugin._get_candidate_skills("s-new")
    uuids = [c["uuid"] for c in candidates]
    assert "s-orig" in uuids
    assert "s-dup" not in uuids


def test_get_candidate_skills_returns_empty_when_only_trigger_exists():
    plugin = _make_plugin_with_mock_llm()
    plugin.set_store_api(_make_mock_store(skills=[
        {"uuid": "s-1", "name": "only", "description": "d", "tags": []},
    ]))
    assert plugin._get_candidate_skills("s-1") == []


def test_get_candidate_skills_returns_empty_when_all_are_duplicates():
    plugin = _make_plugin_with_mock_llm()
    plugin.set_store_api(_make_mock_store(skills=[
        {"uuid": "s-dup1", "tags": ["duplicate:x"]},
        {"uuid": "s-dup2", "tags": ["duplicate:y", "python"]},
    ]))
    assert plugin._get_candidate_skills("s-new") == []


# ── _build_prompt ─────────────────────────────────────────────────────────────

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


# ── _parse_llm_response ───────────────────────────────────────────────────────

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


# ── _apply_duplicate_findings ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_duplicate_findings_writes_tags():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.get_skill.return_value = {"uuid": "s-1", "extra": {}, "tags": []}
    plugin.set_store_api(mock_store)

    await plugin._apply_duplicate_findings("s-1", [{"name": "skill-x", "reason": "same"}])

    mock_store.update_skill_tags.assert_called_once_with("s-1", ["duplicate:skill-x"])


@pytest.mark.asyncio
async def test_apply_duplicate_findings_writes_duplicate_analysis_to_extra():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.get_skill.return_value = {"uuid": "s-1", "extra": {}, "tags": []}
    plugin.set_store_api(mock_store)

    await plugin._apply_duplicate_findings("s-1", [{"name": "skill-x", "reason": "same thing"}])

    mock_store.update_skill_metadata.assert_called_once_with(
        "s-1", {"duplicate_analysis": {"skill-x": "same thing"}}
    )


@pytest.mark.asyncio
async def test_apply_duplicate_findings_preserves_existing_analysis():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.get_skill.return_value = {
        "uuid": "s-1",
        "extra": {"duplicate_analysis": {"skill-old": "old reason"}},
        "tags": [],
    }
    plugin.set_store_api(mock_store)

    await plugin._apply_duplicate_findings("s-1", [{"name": "skill-new", "reason": "new reason"}])

    call_args = mock_store.update_skill_metadata.call_args[0]
    analysis = call_args[1]["duplicate_analysis"]
    assert analysis["skill-old"] == "old reason"
    assert analysis["skill-new"] == "new reason"


@pytest.mark.asyncio
async def test_apply_duplicate_findings_multiple_findings():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.get_skill.return_value = {"uuid": "s-1", "extra": {}, "tags": []}
    plugin.set_store_api(mock_store)

    findings = [
        {"name": "skill-a", "reason": "reason a"},
        {"name": "skill-b", "reason": "reason b"},
    ]
    await plugin._apply_duplicate_findings("s-1", findings)

    mock_store.update_skill_tags.assert_called_once_with(
        "s-1", ["duplicate:skill-a", "duplicate:skill-b"]
    )
    call_args = mock_store.update_skill_metadata.call_args[0]
    analysis = call_args[1]["duplicate_analysis"]
    assert analysis["skill-a"] == "reason a"
    assert analysis["skill-b"] == "reason b"


@pytest.mark.asyncio
async def test_apply_duplicate_findings_no_op_when_empty():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    plugin.set_store_api(mock_store)

    await plugin._apply_duplicate_findings("s-1", [])

    mock_store.update_skill_tags.assert_not_called()
    mock_store.update_skill_metadata.assert_not_called()


# ── _check_for_duplicates ─────────────────────────────────────────────────────

def _skill(uuid, name, description, tags=None):
    return {"uuid": uuid, "name": name, "description": description, "tags": tags or [], "extra": {}}


@pytest.mark.asyncio
async def test_check_for_duplicates_skips_when_skill_not_found():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.get_skill.return_value = None
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock()

    await plugin._check_for_duplicates("missing-uuid")

    plugin.llm_client.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_skips_when_description_too_short():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.get_skill.return_value = _skill("s-1", "x", "short")
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock()

    await plugin._check_for_duplicates("s-1")

    plugin.llm_client.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_skips_when_no_candidates():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store(skills=[
        _skill("s-1", "only skill", "this is a sufficiently long description here"),
    ])
    mock_store.get_skill.return_value = _skill("s-1", "only skill", "this is a sufficiently long description here")
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock()

    await plugin._check_for_duplicates("s-1")

    plugin.llm_client.generate_async.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_no_op_when_llm_returns_empty_array():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "skill", "a sufficiently long description for testing")
    candidate = _skill("s-old", "other", "completely different capability for testing")
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value="[]")

    await plugin._check_for_duplicates("s-new")

    mock_store.update_skill_tags.assert_not_called()
    mock_store.update_skill_metadata.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_tags_skill_when_duplicate_found():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "search tool", "performs web searches and returns ranked results")
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(
        return_value='[{"name": "search tool", "reason": "Both describe web search with ranked results"}]'
    )

    await plugin._check_for_duplicates("s-new")

    mock_store.update_skill_tags.assert_called_once_with("s-new", ["duplicate:search tool"])


@pytest.mark.asyncio
async def test_check_for_duplicates_multiple_duplicates_all_tagged():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "searcher", "searches the web and returns ranked results for any query")
    cand_a = _skill("s-a", "web search", "queries web and returns ranked results for a given input")
    cand_b = _skill("s-b", "search api", "performs web queries returning relevance-ranked results")
    mock_store = _make_mock_store(skills=[trigger, cand_a, cand_b])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(
        return_value='[{"name": "web search", "reason": "same"}, {"name": "search api", "reason": "same"}]'
    )

    await plugin._check_for_duplicates("s-new")

    call_tags = mock_store.update_skill_tags.call_args[0][1]
    assert "duplicate:web search" in call_tags
    assert "duplicate:search api" in call_tags


@pytest.mark.asyncio
async def test_check_for_duplicates_logs_error_on_llm_failure():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "skill", "a sufficiently long description for testing purposes")
    candidate = _skill("s-old", "other", "another sufficiently long description for comparison")
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(side_effect=RuntimeError("API error"))

    await plugin._check_for_duplicates("s-new")  # must not raise

    mock_store.update_skill_tags.assert_not_called()


@pytest.mark.asyncio
async def test_check_for_duplicates_logs_error_on_parse_failure():
    plugin = _make_plugin_with_mock_llm()
    trigger = _skill("s-new", "skill", "a sufficiently long description for testing purposes")
    candidate = _skill("s-old", "other", "another sufficiently long description for comparison")
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value="not valid json at all")

    await plugin._check_for_duplicates("s-new")  # must not raise

    mock_store.update_skill_tags.assert_not_called()


import os


def _make_plugin_in_mode(mode: str):
    """Return a plugin with a mocked LLM client and the given DEDUPE_MODE."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        with patch.dict(os.environ, {"DEDUPE_MODE": mode}):
            from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
            plugin = SkillberryPluginDedupe()
    return plugin


# ── mode ─────────────────────────────────────────────────────────────────────

def test_plugin_defaults_to_interactive_mode():
    with patch.dict(os.environ, {}, clear=True):
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


# ── get_ui_config ─────────────────────────────────────────────────────────────

def test_get_ui_config_returns_notifications_config():
    plugin = _make_plugin_with_mock_llm()
    config = plugin.get_ui_config()
    assert config is not None
    assert "notifications" in config
    notifications = config["notifications"]
    assert "poll_endpoint" in notifications
    assert "/decisions" in notifications["poll_endpoint"]


def test_get_ui_config_notifications_has_keep_and_delete_actions():
    plugin = _make_plugin_with_mock_llm()
    actions = plugin.get_ui_config()["notifications"]["item_schema"]["actions"]
    labels = [a["label"] for a in actions]
    assert "Keep" in labels
    assert "Delete" in labels


def test_get_ui_config_notifications_item_schema_has_required_fields():
    plugin = _make_plugin_with_mock_llm()
    schema = plugin.get_ui_config()["notifications"]["item_schema"]
    assert schema["title_field"] == "skill_name"
    assert "duplicates" in schema["body_fields"]


# ── _check_for_duplicates — interactive mode ──────────────────────────────────

@pytest.mark.asyncio
async def test_check_for_duplicates_creates_pending_decision_in_interactive_mode():
    plugin = _make_plugin_in_mode("interactive")
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "search tool", "performs web searches and returns ranked results")
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
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
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
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
        mock_store = _make_mock_store(skills=[trigger, candidate])
        mock_store.get_skill.return_value = trigger
        plugin.set_store_api(mock_store)
        plugin.llm_client.generate_async = AsyncMock(
            return_value='[{"name": "search tool", "reason": "Both describe web search"}]'
        )

        await plugin._check_for_duplicates("s-new")

        mock_store.update_skill_tags.assert_called_with("s-new", ["duplicate:search tool"])


@pytest.mark.asyncio
async def test_check_for_duplicates_no_pending_decision_when_no_duplicates_found():
    plugin = _make_plugin_in_mode("interactive")
    trigger = _skill("s-new", "web searcher", "searches the web and returns ranked results for any query")
    candidate = _skill("s-old", "other skill", "completely unrelated capability for managing files")
    mock_store = _make_mock_store(skills=[trigger, candidate])
    mock_store.get_skill.return_value = trigger
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value="[]")

    await plugin._check_for_duplicates("s-new")

    assert "s-new" not in plugin._pending_decisions


from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_router_client(plugin) -> TestClient:
    """Mount the plugin's router on a bare FastAPI app for endpoint testing."""
    app = FastAPI()
    router = plugin.get_router()
    app.include_router(router)
    return TestClient(app)


# ── GET /decisions ────────────────────────────────────────────────────────────

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


# ── POST /decisions/{uuid}/keep ───────────────────────────────────────────────

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


# ── POST /decisions/{uuid}/delete ─────────────────────────────────────────────

def test_delete_decision_calls_store_delete_and_removes_pending():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.delete_skill = MagicMock(return_value=True)
    plugin.set_store_api(mock_store)
    plugin._pending_decisions["s-2"] = {
        "uuid": "s-2",
        "skill_name": "Duplicate Skill",
        "duplicates": [],
        "detected_at": "2026-06-18T10:00:00Z",
    }
    client = _make_router_client(plugin)
    response = client.post("/decisions/s-2/delete")
    assert response.status_code == 200
    mock_store.delete_skill.assert_called_once_with("s-2")
    assert "s-2" not in plugin._pending_decisions
    assert "deleted" in response.json()["message"].lower()


def test_delete_decision_returns_404_for_unknown_uuid():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    plugin.set_store_api(mock_store)
    client = _make_router_client(plugin)
    response = client.post("/decisions/nonexistent/delete")
    assert response.status_code == 404


def test_delete_decision_removes_pending_even_when_store_delete_fails():
    plugin = _make_plugin_with_mock_llm()
    mock_store = _make_mock_store()
    mock_store.delete_skill = MagicMock(return_value=False)
    plugin.set_store_api(mock_store)
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
