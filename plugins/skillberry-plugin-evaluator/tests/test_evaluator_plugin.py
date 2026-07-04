"""Tests for the Evaluator Plugin (out-of-process SDK version)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from skillberry_plugin_evaluator.plugin import SkillberryPluginEvaluator
from skillberry_plugin_sdk.testing import dummy_event


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_plugin_with_mock_llm():
    """Create a plugin with a mocked LLM client (no store wired up yet)."""
    plugin = SkillberryPluginEvaluator()
    plugin.llm_client = MagicMock()
    plugin.llm_client.generate_async = AsyncMock()
    plugin._status_message = "Ready (test)"
    return plugin


def _wire_store(plugin, store):
    """Attach an AsyncMock store to a plugin."""
    plugin._store = store
    return plugin


def _llm_json(q=8, p=7):
    return json.dumps(
        {
            "quality_score": q,
            "quality_evaluation": "Good quality.",
            "performance_score": p,
            "performance_evaluation": "Acceptable performance.",
        }
    )


# ── manifest ─────────────────────────────────────────────────────────────────

def test_plugin_manifest_slug():
    plugin = SkillberryPluginEvaluator()
    assert plugin.manifest.slug == "evaluator"


def test_plugin_manifest_type_evaluator():
    plugin = SkillberryPluginEvaluator()
    assert plugin.manifest.plugin_type == "evaluator"


def test_plugin_manifest_version():
    plugin = SkillberryPluginEvaluator()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_has_api():
    plugin = SkillberryPluginEvaluator()
    assert plugin.manifest.has_api is True


def test_plugin_manifest_name():
    plugin = SkillberryPluginEvaluator()
    assert plugin.manifest.name == "Content Evaluator"


# ── enabled / ready state ────────────────────────────────────────────────────

def test_plugin_disabled_when_llm_uninitialized():
    plugin = SkillberryPluginEvaluator()
    assert not plugin.is_enabled()


def test_plugin_enabled_when_llm_set():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.is_enabled()


@pytest.mark.asyncio
async def test_is_ready_false_when_llm_missing():
    plugin = SkillberryPluginEvaluator()
    result = await plugin.is_ready()
    assert result["ready"] is False
    assert "llm_client" in result["missing_config"]


@pytest.mark.asyncio
async def test_is_ready_true_when_llm_set():
    plugin = _make_plugin_with_mock_llm()
    result = await plugin.is_ready()
    assert result["ready"] is True
    assert result["missing_config"] == []


# ── router ───────────────────────────────────────────────────────────────────

def test_plugin_provides_router():
    plugin = _make_plugin_with_mock_llm()
    router = plugin.get_router()
    assert router is not None
    route_paths = [route.path for route in router.routes]
    assert any("evaluate" in path for path in route_paths)


# ── _strip_score_tags ────────────────────────────────────────────────────────

def test_strip_score_tags_removes_quality_and_performance():
    plugin = SkillberryPluginEvaluator()
    tags = ["python", "quality-score:7", "performance-score:5", "utility"]
    assert plugin._strip_score_tags(tags) == ["python", "utility"]


def test_strip_score_tags_no_score_tags_unchanged():
    plugin = SkillberryPluginEvaluator()
    tags = ["python", "utility"]
    assert plugin._strip_score_tags(tags) == ["python", "utility"]


def test_strip_score_tags_empty_list():
    plugin = SkillberryPluginEvaluator()
    assert plugin._strip_score_tags([]) == []


# ── _build_context ───────────────────────────────────────────────────────────

def test_build_context_excludes_previous_evaluation_from_extra():
    plugin = SkillberryPluginEvaluator()
    obj = {
        "name": "my_tool",
        "description": "does something",
        "extra": {
            "custom_key": "keep_me",
            "evaluation": {"quality": {"score": 7, "evaluation": "old text"}},
        },
        "tags": [],
    }
    context = plugin._build_context(obj, "tool")
    assert "keep_me" in context
    assert "old text" not in context
    assert "evaluation" not in context


def test_build_context_tool_includes_key_fields():
    plugin = SkillberryPluginEvaluator()
    obj = {
        "uuid": "tool-1",
        "name": "my_tool",
        "description": "does something useful",
        "programming_language": "python",
        "packaging_format": "code",
        "params": {"type": "object", "properties": {}},
        "tags": ["utility"],
        "extra": {},
    }
    context = plugin._build_context(obj, "tool")
    assert "my_tool" in context
    assert "does something useful" in context
    assert "python" in context


def test_build_context_skill_includes_uuids():
    plugin = SkillberryPluginEvaluator()
    obj = {
        "name": "my_skill",
        "description": "orchestrates things",
        "tool_uuids": ["uuid-a", "uuid-b"],
        "snippet_uuids": ["uuid-c"],
        "tags": [],
        "extra": {},
    }
    context = plugin._build_context(obj, "skill")
    assert "my_skill" in context
    assert "uuid-a" in context
    assert "uuid-c" in context


def test_build_context_snippet_includes_content():
    plugin = SkillberryPluginEvaluator()
    obj = {
        "name": "my_snippet",
        "description": "a greeting",
        "content": "Hello World",
        "content_type": "text/plain",
        "tags": [],
        "extra": {},
    }
    context = plugin._build_context(obj, "snippet")
    assert "Hello World" in context
    assert "my_snippet" in context


# ── evaluate_object ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluate_object_tool_returns_all_four_fields():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_tool = AsyncMock(
        return_value={
            "uuid": "tool-1",
            "name": "test_tool",
            "description": "A test tool",
            "programming_language": "python",
            "packaging_format": "code",
            "params": {},
            "tags": [],
            "extra": {},
        }
    )
    store.update_tool = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=8, p=7))

    result = await plugin.evaluate_object("tool-1", "tool")

    assert result["quality_score"] == 8
    assert result["performance_score"] == 7
    assert result["quality_evaluation"] == "Good quality."
    assert result["performance_evaluation"] == "Acceptable performance."


@pytest.mark.asyncio
async def test_evaluate_object_writes_score_tags_to_tool():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_tool = AsyncMock(
        return_value={
            "uuid": "tool-1",
            "name": "t",
            "description": "",
            "tags": ["existing-tag"],
            "extra": {},
        }
    )
    store.update_tool = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=8, p=7))

    await plugin.evaluate_object("tool-1", "tool")

    store.update_tool.assert_awaited_once()
    _, written = store.update_tool.call_args[0]
    assert "quality-score:8" in written["tags"]
    assert "performance-score:7" in written["tags"]
    assert "existing-tag" in written["tags"]


@pytest.mark.asyncio
async def test_evaluate_object_writes_evaluation_metadata_to_skill():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_skill = AsyncMock(
        return_value={
            "uuid": "skill-1",
            "name": "s",
            "description": "",
            "tool_uuids": [],
            "snippet_uuids": [],
            "tags": [],
            "extra": {},
        }
    )
    store.update_skill = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=6, p=5))

    await plugin.evaluate_object("skill-1", "skill")

    store.update_skill.assert_awaited_once()
    _, written = store.update_skill.call_args[0]
    eval_meta = written["extra"]["evaluation"]
    assert eval_meta["quality"]["score"] == 6
    assert eval_meta["performance"]["score"] == 5
    assert "evaluation" in eval_meta["quality"]
    assert "evaluation" in eval_meta["performance"]
    assert set(eval_meta.keys()) == {"quality", "performance"}


@pytest.mark.asyncio
async def test_evaluate_object_replaces_old_score_tags_on_snippet():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_snippet = AsyncMock(
        return_value={
            "uuid": "snip-1",
            "name": "s",
            "description": "",
            "content": "Hello",
            "content_type": "text/plain",
            "tags": ["keeper", "quality-score:3", "performance-score:2"],
            "extra": {},
        }
    )
    store.update_snippet = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=8, p=7))

    await plugin.evaluate_object("snip-1", "snippet")

    store.update_snippet.assert_awaited_once()
    _, written = store.update_snippet.call_args[0]
    tags = written["tags"]
    assert "quality-score:8" in tags
    assert "quality-score:3" not in tags
    assert "performance-score:7" in tags
    assert "performance-score:2" not in tags
    assert "keeper" in tags


@pytest.mark.asyncio
async def test_evaluate_object_raises_value_error_when_uuid_not_found():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_tool = AsyncMock(return_value=None)
    _wire_store(plugin, store)

    with pytest.raises(ValueError, match="not found"):
        await plugin.evaluate_object("nonexistent", "tool")


@pytest.mark.asyncio
async def test_evaluate_object_raises_runtime_error_on_bad_llm_response():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_tool = AsyncMock(
        return_value={
            "uuid": "t1",
            "name": "t",
            "description": "",
            "tags": [],
            "extra": {},
        }
    )
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value="not json at all")

    with pytest.raises(RuntimeError, match="Failed to parse"):
        await plugin.evaluate_object("t1", "tool")


@pytest.mark.asyncio
async def test_evaluate_object_raises_when_llm_not_initialized():
    plugin = SkillberryPluginEvaluator()
    store = AsyncMock()
    _wire_store(plugin, store)

    with pytest.raises(RuntimeError, match="LLM client not initialized"):
        await plugin.evaluate_object("t1", "tool")


@pytest.mark.asyncio
async def test_evaluate_object_raises_on_unknown_content_type():
    plugin = _make_plugin_with_mock_llm()
    _wire_store(plugin, AsyncMock())

    with pytest.raises(ValueError, match="Unknown content_type"):
        await plugin.evaluate_object("x", "widget")


# ── event handler dispatch ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_on_tool_added_evaluates_tool():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_tool = AsyncMock(
        return_value={
            "uuid": "tool-1",
            "name": "t",
            "description": "",
            "tags": [],
            "extra": {},
        }
    )
    store.update_tool = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json())

    await plugin.on_tool_added(dummy_event("content.tool.added", {"uuid": "tool-1"}))

    store.update_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_snippet_added_evaluates_snippet():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_snippet = AsyncMock(
        return_value={
            "uuid": "snip-1",
            "name": "s",
            "description": "",
            "content": "hello",
            "content_type": "text/plain",
            "tags": [],
            "extra": {},
        }
    )
    store.update_snippet = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json())

    await plugin.on_snippet_added(
        dummy_event("content.snippet.added", {"uuid": "snip-1"})
    )

    store.update_snippet.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_skill_added_evaluates_skill_and_referenced_objects():
    """When a skill is added, its referenced tools and snippets are evaluated too."""
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_skill = AsyncMock(
        return_value={
            "uuid": "skill-1",
            "name": "my_skill",
            "description": "",
            "tool_uuids": ["tool-a"],
            "snippet_uuids": ["snip-b"],
            "tags": [],
            "extra": {},
        }
    )
    store.get_tool = AsyncMock(
        return_value={
            "uuid": "tool-a",
            "name": "tool_a",
            "description": "",
            "tags": [],
            "extra": {},
        }
    )
    store.get_snippet = AsyncMock(
        return_value={
            "uuid": "snip-b",
            "name": "snip_b",
            "description": "",
            "content": "hello",
            "content_type": "text/plain",
            "tags": [],
            "extra": {},
        }
    )
    store.update_skill = AsyncMock()
    store.update_tool = AsyncMock()
    store.update_snippet = AsyncMock()
    _wire_store(plugin, store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json())

    await plugin.on_skill_added(dummy_event("content.skill.added", {"uuid": "skill-1"}))

    assert store.update_skill.await_count == 1
    assert store.update_tool.await_count == 1
    assert store.update_snippet.await_count == 1


@pytest.mark.asyncio
async def test_on_tool_added_ignores_missing_uuid():
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    _wire_store(plugin, store)

    await plugin.on_tool_added(dummy_event("content.tool.added", {}))

    store.get_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_tool_added_noop_when_disabled():
    """Handler must silently return (not raise) when plugin is disabled."""
    plugin = SkillberryPluginEvaluator()  # no llm_client → disabled
    store = AsyncMock()
    _wire_store(plugin, store)

    await plugin.on_tool_added(dummy_event("content.tool.added", {"uuid": "tool-1"}))

    store.get_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_tool_added_swallows_evaluation_errors():
    """Handler must not raise if evaluate_object blows up (auto-eval must be tolerant)."""
    plugin = _make_plugin_with_mock_llm()
    store = AsyncMock()
    store.get_tool = AsyncMock(return_value=None)  # → ValueError inside evaluate
    _wire_store(plugin, store)

    # Should not raise
    await plugin.on_tool_added(dummy_event("content.tool.added", {"uuid": "tool-1"}))


# ── @on_event registration ───────────────────────────────────────────────────

def test_event_handlers_registered_for_all_content_types():
    from skillberry_plugin_sdk.decorators import get_event_handlers

    plugin = SkillberryPluginEvaluator()
    handlers = get_event_handlers(plugin)
    assert "content.tool.added" in handlers
    assert "content.skill.added" in handlers
    assert "content.snippet.added" in handlers
    for topic in ("content.tool.added", "content.skill.added", "content.snippet.added"):
        assert len(handlers[topic]) >= 1


# Made with Bob
