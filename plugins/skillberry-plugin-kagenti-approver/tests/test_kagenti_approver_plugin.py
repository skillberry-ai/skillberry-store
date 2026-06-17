"""Tests for SkillberryPluginKagentiApprover."""
import pytest
from unittest.mock import MagicMock

from skillberry_plugin_kagenti_approver.plugin import (
    parse_criteria,
    evaluate_criteria,
    extract_scores,
    APPROVED_TAG,
    DEFAULT_CRITERIA,
)


# ── parse_criteria ────────────────────────────────────────────────────────────

def test_parse_criteria_default_produces_one_or_group_one_condition():
    groups = parse_criteria(DEFAULT_CRITERIA)
    assert len(groups) == 1
    assert len(groups[0]) == 1


def test_parse_criteria_default_security_score():
    groups = parse_criteria(DEFAULT_CRITERIA)
    tag, op, threshold = groups[0][0]
    assert tag == "security-score"
    assert op == ">="
    assert threshold == 9.0




def test_parse_criteria_or_splits_into_two_groups():
    groups = parse_criteria("security-score>=9|performance-score>=8")
    assert len(groups) == 2
    assert len(groups[0]) == 1
    assert len(groups[1]) == 1


def test_parse_criteria_or_group_has_correct_tags():
    groups = parse_criteria("security-score>=9|performance-score>=8")
    assert groups[0][0][0] == "security-score"
    assert groups[1][0][0] == "performance-score"


def test_parse_criteria_all_operators_parsed():
    s = "a>=1,b>2,c<=3,d<4,e=5,f!=6"
    groups = parse_criteria(s)
    assert len(groups) == 1
    conditions = groups[0]
    assert len(conditions) == 6
    ops = [c[1] for c in conditions]
    assert set(ops) == {">=", ">", "<=", "<", "=", "!="}


def test_parse_criteria_malformed_entry_is_skipped():
    groups = parse_criteria("security-score>=9,not-a-condition,performance-score>=8")
    # malformed middle entry skipped, valid ones kept
    assert len(groups) == 1
    assert len(groups[0]) == 2
    tags = [c[0] for c in groups[0]]
    assert "security-score" in tags
    assert "performance-score" in tags


def test_parse_criteria_non_numeric_threshold_is_skipped():
    groups = parse_criteria("security-score>=nine,performance-score>=8")
    assert len(groups) == 1
    assert len(groups[0]) == 1
    assert groups[0][0][0] == "performance-score"


def test_parse_criteria_empty_string_returns_empty():
    assert parse_criteria("") == []


def test_parse_criteria_all_malformed_or_group_is_dropped():
    # Both conditions malformed → OR group has no valid conditions → dropped
    groups = parse_criteria("bad|security-score>=9")
    # "bad" group is dropped (no valid conditions), "security-score>=9" survives
    assert len(groups) == 1
    assert groups[0][0][0] == "security-score"


# ── extract_scores ────────────────────────────────────────────────────────────

def test_extract_scores_parses_numeric_tags():
    scores = extract_scores(["security-score:9", "performance-score:8"])
    assert scores["security-score"] == 9.0
    assert scores["performance-score"] == 8.0


def test_extract_scores_ignores_non_numeric_value():
    scores = extract_scores(["security-score:high", "performance-score:8"])
    assert "security-score" not in scores
    assert scores["performance-score"] == 8.0


def test_extract_scores_ignores_tags_without_colon():
    scores = extract_scores(["mcp", "imported", "kagenti-approved"])
    assert scores == {}


def test_extract_scores_handles_float_values():
    scores = extract_scores(["quality-score:7.5"])
    assert scores["quality-score"] == 7.5


def test_extract_scores_empty_tags():
    assert extract_scores([]) == {}


def test_extract_scores_skips_colon_without_value():
    scores = extract_scores(["security-score:"])
    assert "security-score" not in scores


# ── evaluate_criteria ─────────────────────────────────────────────────────────

def test_evaluate_criteria_all_and_conditions_met():
    groups = parse_criteria("security-score>=9,performance-score>=8")
    scores = {"security-score": 9.0, "performance-score": 8.0}
    assert evaluate_criteria(groups, scores) is True


def test_evaluate_criteria_one_and_condition_fails():
    groups = parse_criteria("security-score>=9,performance-score>=8")
    scores = {"security-score": 9.0, "performance-score": 7.0}
    assert evaluate_criteria(groups, scores) is False


def test_evaluate_criteria_missing_tag_fails():
    groups = parse_criteria("security-score>=9")
    scores = {"performance-score": 9.0}
    assert evaluate_criteria(groups, scores) is False


def test_evaluate_criteria_or_first_group_passes():
    groups = parse_criteria("security-score>=10|security-score>=9,performance-score>=8")
    scores = {"security-score": 10.0}
    assert evaluate_criteria(groups, scores) is True


def test_evaluate_criteria_or_second_group_passes():
    groups = parse_criteria("security-score>=10|security-score>=9,performance-score>=8")
    scores = {"security-score": 9.0, "performance-score": 8.0}
    assert evaluate_criteria(groups, scores) is True


def test_evaluate_criteria_or_both_groups_fail():
    groups = parse_criteria("security-score>=10|security-score>=9,performance-score>=8")
    scores = {"security-score": 8.0, "performance-score": 8.0}
    assert evaluate_criteria(groups, scores) is False


def test_evaluate_criteria_operator_gt():
    groups = parse_criteria("security-score>9")
    assert evaluate_criteria(groups, {"security-score": 10.0}) is True
    assert evaluate_criteria(groups, {"security-score": 9.0}) is False


def test_evaluate_criteria_operator_lt():
    groups = parse_criteria("security-score<5")
    assert evaluate_criteria(groups, {"security-score": 4.0}) is True
    assert evaluate_criteria(groups, {"security-score": 5.0}) is False


def test_evaluate_criteria_operator_lte():
    groups = parse_criteria("security-score<=5")
    assert evaluate_criteria(groups, {"security-score": 5.0}) is True
    assert evaluate_criteria(groups, {"security-score": 6.0}) is False


def test_evaluate_criteria_operator_eq():
    groups = parse_criteria("security-score=9")
    assert evaluate_criteria(groups, {"security-score": 9.0}) is True
    assert evaluate_criteria(groups, {"security-score": 8.0}) is False


def test_evaluate_criteria_operator_neq():
    groups = parse_criteria("security-score!=9")
    assert evaluate_criteria(groups, {"security-score": 8.0}) is True
    assert evaluate_criteria(groups, {"security-score": 9.0}) is False


def test_evaluate_criteria_empty_groups_returns_false():
    assert evaluate_criteria([], {"security-score": 9.0}) is False


# ── plugin class ──────────────────────────────────────────────────────────────

from skillberry_store.plugins.base import PluginType
from skillberry_plugin_kagenti_approver.plugin import SkillberryPluginKagentiApprover


def test_plugin_metadata_name():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.metadata.name == "Kagenti Approver"


def test_plugin_metadata_type():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.metadata.plugin_type == PluginType.EVALUATOR


def test_plugin_metadata_version():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.metadata.version == "0.1.0"


def test_plugin_is_always_enabled():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.is_enabled() is True


def test_plugin_get_router_returns_none():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.get_router() is None


def test_plugin_get_cli_commands_returns_none():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.get_cli_commands() is None


def test_plugin_get_ui_config_returns_none():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.get_ui_config() is None


# ── _evaluate_skill ───────────────────────────────────────────────────────────

def _make_plugin():
    """Return a plugin with event handlers NOT registered (isolated)."""
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        p = SkillberryPluginKagentiApprover()
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)
    return p


def _mock_store(skill=None):
    store = MagicMock()
    store.get_skill.return_value = skill
    store.update_skill.return_value = True
    store.update_skill_tags.return_value = True
    return store


@pytest.mark.asyncio
async def test_evaluate_skill_approves_when_criteria_met():
    plugin = _make_plugin()
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_called_once_with("s-1", [APPROVED_TAG])


@pytest.mark.asyncio
async def test_evaluate_skill_does_not_approve_when_criteria_not_met():
    plugin = _make_plugin()
    skill = {"uuid": "s-1", "tags": ["security-score:7", "performance-score:8"], "name": "x"}
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_called()
    store.update_skill.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_skill_no_duplicate_tag_when_already_approved():
    plugin = _make_plugin()
    skill = {
        "uuid": "s-1",
        "tags": ["security-score:9", APPROVED_TAG],
        "name": "x",
    }
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    # Tag already present — no write at all
    store.update_skill_tags.assert_not_called()
    store.update_skill.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_skill_revokes_when_criteria_no_longer_met():
    plugin = _make_plugin()
    skill = {
        "uuid": "s-1",
        "tags": ["security-score:6", "performance-score:8", APPROVED_TAG],
        "name": "x",
    }
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill.assert_called_once()
    written_skill = store.update_skill.call_args[0][1]
    assert APPROVED_TAG not in written_skill["tags"]


@pytest.mark.asyncio
async def test_evaluate_skill_revoke_preserves_other_tags():
    plugin = _make_plugin()
    skill = {
        "uuid": "s-1",
        "tags": ["security-score:6", "mcp", "imported", APPROVED_TAG],
        "name": "x",
    }
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    written_skill = store.update_skill.call_args[0][1]
    assert "mcp" in written_skill["tags"]
    assert "imported" in written_skill["tags"]
    assert APPROVED_TAG not in written_skill["tags"]


@pytest.mark.asyncio
async def test_evaluate_skill_no_op_when_criteria_fail_and_not_approved():
    plugin = _make_plugin()
    skill = {"uuid": "s-1", "tags": ["security-score:6", "mcp"], "name": "x"}
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_called()
    store.update_skill.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_skill_skill_not_found_no_crash():
    plugin = _make_plugin()
    store = _mock_store(skill=None)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("missing-uuid")  # must not raise

    store.update_skill_tags.assert_not_called()
    store.update_skill.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_skill_missing_score_tag_fails_criteria():
    plugin = _make_plugin()
    # Only has performance-score, no security-score
    skill = {"uuid": "s-1", "tags": ["performance-score:9"], "name": "x"}
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_called()


# ── event handler registration ────────────────────────────────────────────────

def test_event_handlers_registered_for_skill_added_and_updated():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        SkillberryPluginKagentiApprover()
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
        SkillberryPluginKagentiApprover()
        assert "content_added:tool" not in events_module._event_handlers
        assert "content_added:snippet" not in events_module._event_handlers
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_event_handler_no_op_when_store_not_set():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        SkillberryPluginKagentiApprover()
        handler = events_module._event_handlers["content_added:skill"][0]
        await handler(uuid="any-uuid")  # must not raise
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


# ── env var configuration ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_env_var_overrides_default_criteria(monkeypatch):
    monkeypatch.setenv("KAGENTI_CRITERIA", "security-score>=10")
    plugin = _make_plugin()
    # Score 9 is not enough with the override (needs >=10)
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_called()


@pytest.mark.asyncio
async def test_env_var_override_approves_with_custom_threshold(monkeypatch):
    monkeypatch.setenv("KAGENTI_CRITERIA", "security-score>=9")
    plugin = _make_plugin()
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    store = _mock_store(skill)
    plugin.set_store_api(store)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_called_once_with("s-1", [APPROVED_TAG])


def test_missing_env_var_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("KAGENTI_CRITERIA", raising=False)
    plugin = _make_plugin()
    groups = plugin._load_criteria()
    # Default: security-score>=9 → 1 OR-group, 1 condition
    assert len(groups) == 1
    assert len(groups[0]) == 1
