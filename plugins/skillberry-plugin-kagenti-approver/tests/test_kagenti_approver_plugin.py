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
    assert threshold == 7.0




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


# ── plugin class (SDK-based) ──────────────────────────────────────────────────

from unittest.mock import AsyncMock

from skillberry_plugin_kagenti_approver.plugin import SkillberryPluginKagentiApprover
from skillberry_plugin_sdk.testing import dummy_event


def _plugin_with_store(skill=None):
    """Return a plugin instance with an AsyncMock StoreClient wired in."""
    plugin = SkillberryPluginKagentiApprover()
    store = AsyncMock()
    store.get_skill = AsyncMock(return_value=skill)
    store.update_skill = AsyncMock(return_value=skill)
    store.update_skill_tags = AsyncMock(return_value=skill)
    plugin._store = store
    return plugin, store


def test_plugin_manifest_slug():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.manifest.slug == "kagenti-approver"


def test_plugin_manifest_type_evaluator():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.manifest.plugin_type == "evaluator"


def test_plugin_manifest_version():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_has_no_api_by_default():
    plugin = SkillberryPluginKagentiApprover()
    assert plugin.manifest.has_api is False


# ── _evaluate_skill ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_skill_approves_when_criteria_met():
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_awaited_once_with("s-1", [APPROVED_TAG])


@pytest.mark.asyncio
async def test_evaluate_skill_does_not_approve_when_criteria_not_met():
    skill = {"uuid": "s-1", "tags": ["security-score:6", "performance-score:8"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_awaited()
    store.update_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_evaluate_skill_no_duplicate_tag_when_already_approved():
    skill = {"uuid": "s-1", "tags": ["security-score:9", APPROVED_TAG], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_awaited()
    store.update_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_evaluate_skill_revokes_when_criteria_no_longer_met():
    skill = {
        "uuid": "s-1",
        "tags": ["security-score:6", "performance-score:8", APPROVED_TAG],
        "name": "x",
    }
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill.assert_awaited_once()
    written = store.update_skill.call_args[0][1]
    assert APPROVED_TAG not in written["tags"]


@pytest.mark.asyncio
async def test_evaluate_skill_revoke_preserves_other_tags():
    skill = {
        "uuid": "s-1",
        "tags": ["security-score:6", "mcp", "imported", APPROVED_TAG],
        "name": "x",
    }
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    written = store.update_skill.call_args[0][1]
    assert "mcp" in written["tags"]
    assert "imported" in written["tags"]
    assert APPROVED_TAG not in written["tags"]


@pytest.mark.asyncio
async def test_evaluate_skill_no_op_when_criteria_fail_and_not_approved():
    skill = {"uuid": "s-1", "tags": ["security-score:6", "mcp"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_awaited()
    store.update_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_evaluate_skill_skill_not_found_no_crash():
    plugin, store = _plugin_with_store(skill=None)

    await plugin._evaluate_skill("missing-uuid")

    store.update_skill_tags.assert_not_awaited()
    store.update_skill.assert_not_awaited()


@pytest.mark.asyncio
async def test_evaluate_skill_missing_score_tag_fails_criteria():
    skill = {"uuid": "s-1", "tags": ["performance-score:9"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_awaited()


# ── event handler dispatch ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_on_skill_change_dispatches_evaluate():
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin.on_skill_change(dummy_event("content.skill.added", {"uuid": "s-1"}))

    store.update_skill_tags.assert_awaited_once_with("s-1", [APPROVED_TAG])


@pytest.mark.asyncio
async def test_on_skill_change_ignores_missing_uuid():
    plugin, store = _plugin_with_store(skill=None)
    await plugin.on_skill_change(dummy_event("content.skill.updated", {}))
    store.get_skill.assert_not_awaited()


# ── env var configuration ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_env_var_overrides_default_criteria(monkeypatch):
    monkeypatch.setenv("KAGENTI_CRITERIA", "security-score>=10")
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_not_awaited()


@pytest.mark.asyncio
async def test_env_var_override_approves_with_custom_threshold(monkeypatch):
    monkeypatch.setenv("KAGENTI_CRITERIA", "security-score>=9")
    skill = {"uuid": "s-1", "tags": ["security-score:9"], "name": "x"}
    plugin, store = _plugin_with_store(skill)

    await plugin._evaluate_skill("s-1")

    store.update_skill_tags.assert_awaited_once_with("s-1", [APPROVED_TAG])


def test_missing_env_var_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("KAGENTI_CRITERIA", raising=False)
    plugin = SkillberryPluginKagentiApprover()
    groups = plugin._load_criteria()
    assert len(groups) == 1
    assert len(groups[0]) == 1
