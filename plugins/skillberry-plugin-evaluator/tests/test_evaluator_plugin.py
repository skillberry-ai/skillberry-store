"""Tests for the Evaluator Plugin."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from skillberry_plugin_evaluator.plugin import SkillberryPluginEvaluator
from skillberry_store.plugins.base import PluginType


# ── existing structural tests ────────────────────────────────────────────────

def test_plugin_metadata():
    plugin = SkillberryPluginEvaluator()
    metadata = plugin.metadata
    assert metadata.name == "Content Evaluator"
    assert metadata.plugin_type == PluginType.EVALUATOR
    assert metadata.version == "0.1.0"
    assert "evaluate" in metadata.description.lower() or "tag" in metadata.description.lower()


def test_plugin_disabled_when_llm_unavailable():
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginEvaluator()
        assert not plugin.is_enabled()


def test_plugin_enabled_when_llm_available():
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginEvaluator()
        assert plugin.is_enabled()


def test_plugin_provides_router():
    plugin = SkillberryPluginEvaluator()
    router = plugin.get_router()
    assert router is not None
    route_paths = [route.path for route in router.routes]
    assert any("evaluate" in path for path in route_paths)


def test_plugin_provides_no_cli_commands():
    plugin = SkillberryPluginEvaluator()
    assert plugin.get_cli_commands() is None


def test_plugin_provides_ui_config():
    plugin = SkillberryPluginEvaluator()
    ui_config = plugin.get_ui_config()
    assert ui_config is not None
    assert "icon" in ui_config
    assert "color" in ui_config
    assert "actions" in ui_config
    assert len(ui_config["actions"]) > 0
    action_labels = [action["label"] for action in ui_config["actions"]]
    assert any("evaluate" in label.lower() for label in action_labels)


# ── helper: _strip_score_tags ────────────────────────────────────────────────

def test_strip_score_tags_removes_all_score_types():
    plugin = SkillberryPluginEvaluator()
    # includes security-score to ensure old 3-category evaluations are cleaned up
    tags = ["python", "quality-score:7", "performance-score:5", "security-score:8", "utility"]
    assert plugin._strip_score_tags(tags) == ["python", "utility"]


def test_strip_score_tags_no_score_tags_unchanged():
    plugin = SkillberryPluginEvaluator()
    tags = ["python", "utility"]
    assert plugin._strip_score_tags(tags) == ["python", "utility"]


def test_strip_score_tags_empty_list():
    plugin = SkillberryPluginEvaluator()
    assert plugin._strip_score_tags([]) == []


# ── helper: _build_context ───────────────────────────────────────────────────

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

def _make_plugin_with_mock_llm():
    """Create a plugin instance with a mocked LLM client."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginEvaluator()
    return plugin


def _llm_json(q=8, p=7):
    return json.dumps({
        "quality_score": q,
        "quality_evaluation": "Good quality.",
        "performance_score": p,
        "performance_evaluation": "Acceptable performance.",
    })


@pytest.mark.asyncio
async def test_evaluate_object_tool_returns_all_six_fields():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = {
        "uuid": "tool-1", "name": "test_tool", "description": "A test tool",
        "programming_language": "python", "packaging_format": "code",
        "params": {}, "tags": [], "extra": {},
    }
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=8, p=7))

    result = await plugin.evaluate_object("tool-1", "tool")

    assert result["quality_score"] == 8
    assert result["performance_score"] == 7
    assert result["quality_evaluation"] == "Good quality."
    assert result["performance_evaluation"] == "Acceptable performance."


@pytest.mark.asyncio
async def test_evaluate_object_writes_score_tags_to_tool():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = {
        "uuid": "tool-1", "name": "t", "description": "",
        "tags": ["existing-tag"], "extra": {},
    }
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=8, p=7))

    await plugin.evaluate_object("tool-1", "tool")

    written = mock_store.tools.write_dict.call_args[0][1]
    assert "quality-score:8" in written["tags"]
    assert "performance-score:7" in written["tags"]
    assert "existing-tag" in written["tags"]


@pytest.mark.asyncio
async def test_evaluate_object_writes_evaluation_metadata_to_skill():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_skill.return_value = {
        "uuid": "skill-1", "name": "s", "description": "",
        "tool_uuids": [], "snippet_uuids": [], "tags": [], "extra": {},
    }
    mock_store.skills = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=6, p=5))

    await plugin.evaluate_object("skill-1", "skill")

    written = mock_store.skills.write_dict.call_args[0][1]
    eval_meta = written["extra"]["evaluation"]
    assert eval_meta["quality"]["score"] == 6
    assert eval_meta["performance"]["score"] == 5
    assert "evaluation" in eval_meta["quality"]
    assert "evaluation" in eval_meta["performance"]
    assert "security" not in eval_meta


@pytest.mark.asyncio
async def test_evaluate_object_replaces_old_score_tags_on_snippet():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_snippet.return_value = {
        "uuid": "snip-1", "name": "s", "description": "",
        "content": "Hello", "content_type": "text/plain",
        "tags": ["keeper", "quality-score:3", "performance-score:2"],
        "extra": {},
    }
    mock_store.snippets = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(q=8, p=7))

    await plugin.evaluate_object("snip-1", "snippet")

    written = mock_store.snippets.write_dict.call_args[0][1]
    tags = written["tags"]
    assert "quality-score:8" in tags
    assert "quality-score:3" not in tags
    assert "performance-score:7" in tags
    assert "performance-score:2" not in tags
    assert "keeper" in tags


@pytest.mark.asyncio
async def test_evaluate_object_raises_value_error_when_uuid_not_found():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = None
    plugin.set_store_api(mock_store)

    with pytest.raises(ValueError, match="not found"):
        await plugin.evaluate_object("nonexistent", "tool")


@pytest.mark.asyncio
async def test_evaluate_object_raises_runtime_error_on_bad_llm_response():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = {
        "uuid": "t1", "name": "t", "description": "", "tags": [], "extra": {},
    }
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value="not json at all")

    with pytest.raises(RuntimeError, match="Failed to parse"):
        await plugin.evaluate_object("t1", "tool")


@pytest.mark.asyncio
async def test_skill_content_added_also_evaluates_referenced_tools_and_snippets():
    """When a skill is added, its referenced tools and snippets are evaluated too.

    This covers import flows (e.g. import-anthropic-skill) that write tools/snippets
    directly without emitting per-object content_added events.
    """
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()

    mock_store.get_skill.return_value = {
        "uuid": "skill-1", "name": "my_skill", "description": "",
        "tool_uuids": ["tool-a"], "snippet_uuids": ["snip-b"], "tags": [], "extra": {},
    }
    mock_store.get_tool.return_value = {
        "uuid": "tool-a", "name": "tool_a", "description": "", "tags": [], "extra": {},
    }
    mock_store.get_snippet.return_value = {
        "uuid": "snip-b", "name": "snip_b", "description": "",
        "content": "hello", "content_type": "text/plain", "tags": [], "extra": {},
    }
    mock_store.skills = MagicMock()
    mock_store.tools = MagicMock()
    mock_store.snippets = MagicMock()

    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json())

    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        from skillberry_store.plugins.events import _event_handlers
        from unittest.mock import patch
        mock_module = MagicMock()
        mock_module.get_llm.return_value = MagicMock(return_value=plugin.llm_client)
        with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
            pass  # handlers already registered on plugin
        # Register the existing plugin's handlers manually
        _event_handlers.setdefault("content_added:skill", [])
        # Re-register by creating a fresh plugin with the same mock store
        fresh_plugin = _make_plugin_with_mock_llm()
        fresh_plugin.set_store_api(mock_store)
        fresh_plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json())

        handler = _event_handlers["content_added:skill"][0]
        await handler(uuid="skill-1")

        # skill, tool, and snippet should each have write_dict called
        assert mock_store.skills.write_dict.called
        assert mock_store.tools.write_dict.called
        assert mock_store.snippets.write_dict.called
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


# ── event handler tests ──────────────────────────────────────────────────────

def test_event_handlers_registered_for_all_content_types():
    from skillberry_store.plugins import events as events_module

    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        mock_module = MagicMock()
        mock_module.get_llm.side_effect = RuntimeError("unavailable")
        with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
            SkillberryPluginEvaluator()

        assert len(events_module._event_handlers.get("content_added:tool", [])) > 0
        assert len(events_module._event_handlers.get("content_added:skill", [])) > 0
        assert len(events_module._event_handlers.get("content_added:snippet", [])) > 0
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_auto_evaluation_skipped_when_store_not_set():
    """Handler must silently return (not raise) when store has not been injected yet."""
    from skillberry_store.plugins import events as events_module

    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        mock_client = MagicMock()
        mock_llm_class = MagicMock(return_value=mock_client)
        mock_module = MagicMock()
        mock_module.get_llm.return_value = mock_llm_class
        with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
            SkillberryPluginEvaluator()

        handler = events_module._event_handlers["content_added:tool"][0]
        await handler(uuid="any-uuid")  # must not raise
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


# Made with Bob
